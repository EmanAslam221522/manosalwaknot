from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.database import get_db
from app.core.errors import ApiError
from app.models import DeviceToken, Notification, User
from app.schemas import DeviceIn, NotificationOut, NotificationPage

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationPage)
def list_notifications(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    total = db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user.id)) or 0
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    items = [NotificationOut(id=row.id, type=row.type, title=row.title, body=row.body, read_at=row.read_at, created_at=row.created_at, route=row.route) for row in rows]
    return {"items": items, "meta": {"page": page, "page_size": page_size, "total": total, "total_pages": (total + page_size - 1) // page_size}}


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def read_notification(notification_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    notification = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id))
    if notification is None:
        raise ApiError(404, "NOTIFICATION_NOT_FOUND", "This notification was not found.")
    notification.read_at = notification.read_at or datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/devices", status_code=status.HTTP_204_NO_CONTENT)
def register_device(payload: DeviceIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    existing = db.scalar(select(DeviceToken).where(DeviceToken.token == payload.token))
    if existing:
        existing.user_id, existing.platform, existing.active = user.id, payload.platform, True
    else:
        db.add(DeviceToken(user_id=user.id, token=payload.token, platform=payload.platform))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
