import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.core.security import hash_opaque_token
from app.domain import audit
from app.models import FoodListing, HandoverToken, Notification, Report, Reservation, ReservationEvent, ReservationStatus, Role, User, VerificationRequest, VerificationStatus, VerificationType
from app.schemas import HandoverConfirm, HandoverConfirmOut, HandoverTokenOut, ReportCreate, ReportOut, VerificationCreate, VerificationOut

router = APIRouter(tags=["trust"])


@router.get("/verification-requests/me", response_model=list[VerificationOut])
def my_verifications(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[VerificationOut]:
    records = {item.type: item for item in db.scalars(select(VerificationRequest).where(VerificationRequest.user_id == user.id)).all()}
    return [VerificationOut(id=records[kind].id if kind in records else None, type=kind, status=records[kind].status if kind in records else "NOT_SUBMITTED", submitted_at=records[kind].submitted_at if kind in records else None, reviewer_message=records[kind].reviewer_message if kind in records else None) for kind in VerificationType]


@router.post("/verification-requests", response_model=VerificationOut, status_code=status.HTTP_201_CREATED)
def submit_verification(payload: VerificationCreate, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> VerificationOut:
    existing = db.scalar(select(VerificationRequest).where(VerificationRequest.user_id == user.id, VerificationRequest.type == payload.type).with_for_update())
    if existing and existing.status in {VerificationStatus.PENDING, VerificationStatus.APPROVED}:
        raise ApiError(409, "VERIFICATION_ALREADY_ACTIVE", "A verification request is already active.")
    if existing:
        existing.statement, existing.status, existing.submitted_at, existing.reviewer_message = payload.statement, VerificationStatus.PENDING, datetime.now(UTC), None
        record = existing
    else:
        record = VerificationRequest(user_id=user.id, type=payload.type, statement=payload.statement)
        db.add(record)
        db.flush()
    audit(db, user.id, "verification.submitted", "verification_request", record.id, request.state.request_id)
    db.commit()
    return VerificationOut(id=record.id, type=record.type, status=record.status, submitted_at=record.submitted_at, reviewer_message=record.reviewer_message)


@router.post("/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ReportOut:
    if payload.food_listing_id and db.get(FoodListing, payload.food_listing_id) is None:
        raise ApiError(404, "REPORT_TARGET_NOT_FOUND", "The item you are reporting was not found.")
    if payload.reservation_id:
        reservation = db.scalar(select(Reservation).options(selectinload(Reservation.food)).where(Reservation.id == payload.reservation_id))
        roles = {entry.role for entry in user.roles}
        if reservation is None or (user.id not in {reservation.recipient_id, reservation.food.provider_id} and not roles.intersection({Role.ADMIN, Role.SUPER_ADMIN})):
            raise ApiError(404, "REPORT_TARGET_NOT_FOUND", "The item you are reporting was not found.")
    report = Report(reporter_id=user.id, food_listing_id=payload.food_listing_id, reservation_id=payload.reservation_id, reason=payload.reason, details=payload.details)
    db.add(report)
    db.flush()
    audit(db, user.id, "report.created", "report", report.id, request.state.request_id)
    db.commit()
    return ReportOut(id=report.id, reason=report.reason, status=report.status, created_at=report.created_at, updated_at=report.updated_at)


@router.post("/reservations/{reservation_id}/handover-token", response_model=HandoverTokenOut)
def create_handover_token(reservation_id: str, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> HandoverTokenOut:
    reservation = db.scalar(select(Reservation).where(Reservation.id == reservation_id).with_for_update())
    if reservation is None or reservation.recipient_id != user.id:
        raise ApiError(404, "RESERVATION_NOT_FOUND", "This reservation was not found.")
    if reservation.status not in {ReservationStatus.CONFIRMED, ReservationStatus.READY}:
        raise ApiError(409, "HANDOVER_NOT_AVAILABLE", "Handover is not available for this reservation.")
    db.execute(
        select(HandoverToken)
        .where(
            HandoverToken.reservation_id == reservation.id,
            HandoverToken.consumed_at.is_(None),
        )
        .with_for_update()
    )
    now = datetime.now(UTC)
    for previous_token in db.scalars(
        select(HandoverToken).where(
            HandoverToken.reservation_id == reservation.id,
            HandoverToken.consumed_at.is_(None),
        )
    ):
        previous_token.consumed_at = now
    token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=get_settings().handover_token_minutes)
    db.add(HandoverToken(reservation_id=reservation.id, token_hash=hash_opaque_token(token), expires_at=expires_at))
    audit(db, user.id, "handover_token.created", "reservation", reservation.id, request.state.request_id)
    db.commit()
    return HandoverTokenOut(token=token, expires_at=expires_at)


@router.post("/handovers/confirm", response_model=HandoverConfirmOut)
def confirm_handover(payload: HandoverConfirm, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> HandoverConfirmOut:
    token_hash = hash_opaque_token(payload.token)
    candidate = db.scalar(select(HandoverToken).where(HandoverToken.token_hash == token_hash))
    if candidate is None:
        raise ApiError(409, "HANDOVER_TOKEN_INVALID", "This handover code is invalid or has expired.")
    reservation = db.scalar(select(Reservation).options(selectinload(Reservation.food)).where(Reservation.id == candidate.reservation_id).with_for_update())
    record = db.scalar(select(HandoverToken).where(HandoverToken.id == candidate.id).with_for_update())
    if record is None or record.consumed_at is not None or record.expires_at <= datetime.now(UTC):
        raise ApiError(409, "HANDOVER_TOKEN_INVALID", "This handover code is invalid or has expired.")
    if reservation is None or reservation.food.provider_id != user.id:
        raise ApiError(404, "RESERVATION_NOT_FOUND", "This reservation was not found.")
    if reservation.status not in {ReservationStatus.CONFIRMED, ReservationStatus.READY}:
        raise ApiError(409, "HANDOVER_ALREADY_COMPLETED", "This handover has already been processed.")
    previous = reservation.status
    reservation.status = ReservationStatus.PICKED_UP
    record.consumed_at, record.consumed_by_id = datetime.now(UTC), user.id
    db.add(ReservationEvent(reservation_id=reservation.id, actor_id=user.id, previous_state=previous, new_state=ReservationStatus.PICKED_UP, request_id=request.state.request_id, actor_label=user.display_name))
    db.add(Notification(user_id=reservation.recipient_id, type="handover_confirmed", title="Pickup confirmed", body="Your food pickup was confirmed.", route=f"/reservations/{reservation.id}"))
    audit(db, user.id, "handover.confirmed", "reservation", reservation.id, request.state.request_id)
    db.commit()
    return HandoverConfirmOut(reservation_id=reservation.id)
