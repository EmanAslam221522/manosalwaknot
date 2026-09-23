import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_opaque_token, new_opaque_token
from app.models import AuditLog, FoodListing, Reservation, Role, Session as UserSession, User
from app.schemas import FoodDetailOut, FoodSummaryOut, PageMeta, ReservationDetailOut, ReservationEventOut, ReservationSummaryOut, SessionOut, TokensOut, UserOut


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, display_name=user.display_name, email=user.email, phone_number=user.phone_number, roles=[entry.role for entry in user.roles], city=user.city, area=user.area, is_verified=user.is_verified)


def issue_session(db: Session, user: User) -> SessionOut:
    token = new_opaque_token()
    session = UserSession(user_id=user.id, refresh_token_hash=hash_opaque_token(token), expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days))
    db.add(session)
    db.flush()
    return SessionOut(access_token=create_access_token(user.id, session.id), refresh_token=token, user=user_out(user))


def rotate_session(db: Session, old: UserSession) -> TokensOut:
    token = new_opaque_token()
    replacement = UserSession(user_id=old.user_id, refresh_token_hash=hash_opaque_token(token), expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days))
    db.add(replacement)
    db.flush()
    old.revoked_at = datetime.now(UTC)
    old.replaced_by_id = replacement.id
    return TokensOut(access_token=create_access_token(old.user_id, replacement.id), refresh_token=token)


def audit(db: Session, actor_id: UUID | None, action: str, target_type: str, target_id: UUID | None, request_id: str, extra: dict[str, object] | None = None) -> None:
    db.add(AuditLog(actor_id=actor_id, action=action, target_type=target_type, target_id=target_id, request_id=request_id, extra=extra or {}))


def pagination(total: int, page: int, page_size: int) -> PageMeta:
    return PageMeta(page=page, page_size=page_size, total_items=total, total_pages=math.ceil(total / page_size) if total else 0)


def distance_km(lat1: float, lng1: float, lat2: Decimal, lng2: Decimal) -> float:
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(float(lat2))
    dp = math.radians(float(lat2) - lat1)
    dl = math.radians(float(lng2) - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1)


def can_view_exact_food(user: User, food: FoodListing, db: Session) -> bool:
    roles = {entry.role for entry in user.roles}
    if food.provider_id == user.id or roles.intersection({Role.ADMIN, Role.SUPER_ADMIN}):
        return True
    count = db.scalar(select(func.count()).select_from(Reservation).where(Reservation.food_listing_id == food.id, Reservation.recipient_id == user.id)) or 0
    return count > 0


def food_summary(food: FoodListing, lat: float | None = None, lng: float | None = None) -> FoodSummaryOut:
    distance = distance_km(lat, lng, food.latitude, food.longitude) if lat is not None and lng is not None else None
    return FoodSummaryOut(id=food.id, title=food.title, provider_name=food.provider.display_name, provider_verified=food.provider.is_verified, image_url=food.image_url, servings_available=food.servings_available, is_free=food.is_free, price=food.price, currency=food.currency, pickup_start=food.pickup_start, pickup_end=food.pickup_end, area=food.area, approximate_distance_km=distance, status=food.status, dietary_information=food.dietary_information)


def food_detail(food: FoodListing, exact: bool, lat: float | None = None, lng: float | None = None) -> FoodDetailOut:
    return FoodDetailOut(**food_summary(food, lat, lng).model_dump(), description=food.description, category_id=food.category_id, quantity=food.quantity, unit=food.unit, ingredients=food.ingredients, allergens=food.allergens, storage_information=food.storage_information, expires_at=food.expires_at, exact_pickup_address=food.location.address if exact else None, latitude=float(food.latitude) if exact else None, longitude=float(food.longitude) if exact else None)


def reservation_summary(reservation: Reservation) -> ReservationSummaryOut:
    return ReservationSummaryOut(id=reservation.id, food=food_summary(reservation.food), quantity=reservation.quantity, status=reservation.status, pickup_start=reservation.food.pickup_start, pickup_end=reservation.food.pickup_end, updated_at=reservation.updated_at)


def reservation_detail(reservation: Reservation, events: list[object], can_show: bool, handover_token: str | None = None) -> ReservationDetailOut:
    event_outputs = [ReservationEventOut(id=getattr(event, "id"), previous_state=getattr(event, "previous_state"), new_state=getattr(event, "new_state"), occurred_at=getattr(event, "occurred_at"), actor_label=getattr(event, "actor_label")) for event in events]
    return ReservationDetailOut(**reservation_summary(reservation).model_dump(), pickup_address=reservation.pickup_address if can_show else None, handover_instructions=reservation.handover_instructions if can_show else None, can_display_handover_qr=can_show, handover_token=handover_token, events=event_outputs)
