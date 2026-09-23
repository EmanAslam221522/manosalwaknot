from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.models import Role, Session as UserSession, User

bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "AUTHENTICATION_REQUIRED", "Please sign in to continue.")
    user_id, session_id = decode_access_token(credentials.credentials)
    user_session = db.get(UserSession, session_id)
    if user_session is None or user_session.user_id != user_id or user_session.revoked_at is not None:
        raise ApiError(401, "SESSION_REVOKED", "Your session is no longer valid.")
    user = db.scalar(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    if user is None or not user.is_active or user.deleted_at is not None:
        raise ApiError(401, "ACCOUNT_UNAVAILABLE", "Your account is unavailable.")
    return user


def role_values(user: User) -> set[Role]:
    return {entry.role for entry in user.roles}


def require_roles(*roles: Role) -> Callable[[User], User]:
    def dependency(user: User = Depends(current_user)) -> User:
        if not role_values(user).intersection(roles):
            raise ApiError(403, "ROLE_REQUIRED", "You are not authorized to perform this action.")
        return user

    return dependency
