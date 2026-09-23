import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.core.rate_limit import enforce_rate_limit
from app.core.security import hash_opaque_token, hash_password, verify_password
from app.domain import audit, issue_session, rotate_session, user_out
from app.models import OtpChallenge, Role, Session as UserSession, User, UserRole
from app.schemas import EmailRegister, OtpRequest, OtpVerify, PasswordLogin, RefreshRequest, SessionOut, TokensOut, UserOut

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register/email", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def register_email(payload: EmailRegister, request: Request, db: Session = Depends(get_db)) -> SessionOut:
    enforce_rate_limit(request, "register", 5, 3600)
    email = payload.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise ApiError(409, "EMAIL_ALREADY_REGISTERED", "An account already uses this email.")
    user = User(display_name=payload.display_name, email=email, password_hash=hash_password(payload.password))
    user.roles.append(UserRole(role=Role.RECIPIENT))
    db.add(user)
    db.flush()
    result = issue_session(db, user)
    audit(db, user.id, "user.registered", "user", user.id, request.state.request_id)
    db.commit()
    return result


@router.post("/login/password", response_model=SessionOut)
def login_password(payload: PasswordLogin, request: Request, db: Session = Depends(get_db)) -> SessionOut:
    enforce_rate_limit(request, "password_login", 10, 900)
    user = db.scalar(select(User).options(selectinload(User.roles)).where(User.email == payload.email.lower()))
    if user is None or user.password_hash is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise ApiError(401, "INVALID_CREDENTIALS", "The email or password is incorrect.")
    result = issue_session(db, user)
    audit(db, user.id, "session.created", "user", user.id, request.state.request_id)
    db.commit()
    return result


@router.post("/otp/request", status_code=status.HTTP_204_NO_CONTENT)
def request_otp(payload: OtpRequest, request: Request, db: Session = Depends(get_db)) -> Response:
    enforce_rate_limit(request, "otp_request", 5, 900)
    settings = get_settings()
    if settings.environment != "development" and settings.otp_debug_code is None:
        raise ApiError(503, "SMS_PROVIDER_NOT_CONFIGURED", "Phone sign-in is temporarily unavailable.")
    code = settings.otp_debug_code.get_secret_value() if settings.otp_debug_code else f"{secrets.randbelow(1_000_000):06d}"
    challenge = OtpChallenge(phone_number=payload.phone_number, code_hash=hash_opaque_token(code), expires_at=datetime.now(UTC) + timedelta(minutes=5))
    db.add(challenge)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/otp/verify", response_model=SessionOut)
def verify_otp(payload: OtpVerify, request: Request, db: Session = Depends(get_db)) -> SessionOut:
    enforce_rate_limit(request, "otp_verify", 10, 900)
    challenge = db.scalar(select(OtpChallenge).where(OtpChallenge.phone_number == payload.phone_number, OtpChallenge.consumed_at.is_(None)).order_by(OtpChallenge.created_at.desc()).with_for_update())
    if challenge is None or challenge.expires_at <= datetime.now(UTC) or challenge.attempts >= 5:
        raise ApiError(401, "OTP_INVALID_OR_EXPIRED", "The code is invalid or has expired.")
    challenge.attempts += 1
    if not secrets.compare_digest(challenge.code_hash, hash_opaque_token(payload.otp)):
        db.commit()
        raise ApiError(401, "OTP_INVALID_OR_EXPIRED", "The code is invalid or has expired.")
    challenge.consumed_at = datetime.now(UTC)
    user = db.scalar(select(User).options(selectinload(User.roles)).where(User.phone_number == payload.phone_number))
    if user is None:
        user = User(display_name="Community member", phone_number=payload.phone_number)
        user.roles.append(UserRole(role=Role.RECIPIENT))
        db.add(user)
        db.flush()
    result = issue_session(db, user)
    audit(db, user.id, "session.created.otp", "user", user.id, request.state.request_id)
    db.commit()
    return result


@router.post("/refresh", response_model=TokensOut)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokensOut:
    enforce_rate_limit(request, "refresh", 30, 900)
    old = db.scalar(select(UserSession).where(UserSession.refresh_token_hash == hash_opaque_token(payload.refresh_token)).with_for_update())
    if old is None or old.expires_at <= datetime.now(UTC):
        raise ApiError(401, "REFRESH_TOKEN_INVALID", "Please sign in again.")
    if old.revoked_at is not None:
        db.execute(
            update(UserSession)
            .where(UserSession.family_id == old.family_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        audit(db, old.user_id, "session.refresh_reuse_detected", "session", old.id, request.state.request_id)
        db.commit()
        raise ApiError(401, "REFRESH_TOKEN_REUSED", "Please sign in again.")
    result = rotate_session(db, old)
    audit(db, old.user_id, "session.rotated", "session", old.id, request.state.request_id)
    db.commit()
    return result


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    credentials = request.headers.get("authorization", "").removeprefix("Bearer ")
    from app.core.security import decode_access_token
    _, session_id = decode_access_token(credentials)
    session = db.get(UserSession, session_id)
    if session:
        session.revoked_at = datetime.now(UTC)
    audit(db, user.id, "session.revoked", "session", session_id, request.state.request_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
