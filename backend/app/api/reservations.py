from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user
from app.core.database import get_db
from app.core.errors import ApiError
from app.domain import audit, pagination, reservation_detail, reservation_summary
from app.models import DeliveryStatus, DeliveryTask, FoodListing, Notification, Reservation, ReservationEvent, ReservationStatus, Role, User
from app.reservations.service import ACTIVE_STATES, create_reservation
from app.schemas import ReservationCreate, ReservationDetailOut, ReservationPage, ReservationSummaryOut

router = APIRouter(prefix="/reservations", tags=["reservations"])


def reservation_load() -> tuple[object, object]:
    return selectinload(Reservation.food).selectinload(FoodListing.provider), selectinload(Reservation.food).selectinload(FoodListing.location)


def authorized(reservation: Reservation, user: User) -> bool:
    roles = {entry.role for entry in user.roles}
    return user.id in {reservation.recipient_id, reservation.food.provider_id} or bool(roles.intersection({Role.ADMIN, Role.SUPER_ADMIN}))


@router.get("", response_model=ReservationPage)
def list_reservations(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(current_user), db: Session = Depends(get_db)) -> ReservationPage:
    condition = or_(Reservation.recipient_id == user.id, Reservation.food.has(FoodListing.provider_id == user.id))
    total = db.scalar(select(func.count()).select_from(Reservation).where(condition)) or 0
    records = db.scalars(select(Reservation).options(*reservation_load()).where(condition).order_by(Reservation.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return ReservationPage(items=[reservation_summary(item) for item in records], meta=pagination(total, page, page_size))


@router.post("", response_model=ReservationDetailOut, status_code=status.HTTP_201_CREATED)
def post_reservation(
    payload: ReservationCreate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ReservationDetailOut:
    reservation, event = create_reservation(
        db,
        food_listing_id=payload.food_listing_id,
        recipient=user,
        quantity=payload.quantity,
        request_id=request.state.request_id,
        actor=user,
    )
    db.commit()
    return reservation_detail(reservation, [event], True)


@router.get("/{reservation_id}", response_model=ReservationDetailOut)
def get_reservation(reservation_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ReservationDetailOut:
    reservation = db.scalar(select(Reservation).options(*reservation_load()).where(Reservation.id == reservation_id))
    if reservation is None or not authorized(reservation, user):
        raise ApiError(404, "RESERVATION_NOT_FOUND", "This reservation was not found.")
    events = list(db.scalars(select(ReservationEvent).where(ReservationEvent.reservation_id == reservation.id).order_by(ReservationEvent.occurred_at)).all())
    can_show = reservation.status in ACTIVE_STATES | {ReservationStatus.PICKED_UP, ReservationStatus.DELIVERED}
    return reservation_detail(reservation, events, can_show)


@router.post("/{reservation_id}/cancel", response_model=ReservationDetailOut)
def cancel_reservation(reservation_id: UUID, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ReservationDetailOut:
    reservation = db.scalar(select(Reservation).options(*reservation_load()).where(Reservation.id == reservation_id).with_for_update())
    if reservation is None or not authorized(reservation, user):
        raise ApiError(404, "RESERVATION_NOT_FOUND", "This reservation was not found.")
    if reservation.status not in ACTIVE_STATES:
        raise ApiError(409, "INVALID_RESERVATION_TRANSITION", "This reservation can no longer be cancelled.")
    delivery = db.scalar(select(DeliveryTask).where(DeliveryTask.reservation_id == reservation.id).with_for_update())
    if delivery is not None and delivery.status != DeliveryStatus.CANCELLED:
        raise ApiError(409, "DELIVERY_ALREADY_SCHEDULED", "Cancel the delivery arrangement before cancelling this reservation.")
    previous = reservation.status
    reservation.status = ReservationStatus.CANCELLED
    reservation.food.servings_available += reservation.quantity
    event = ReservationEvent(reservation_id=reservation.id, actor_id=user.id, previous_state=previous, new_state=ReservationStatus.CANCELLED, request_id=request.state.request_id, actor_label=user.display_name)
    db.add(event)
    db.flush()
    target = reservation.food.provider_id if user.id == reservation.recipient_id else reservation.recipient_id
    db.add(Notification(user_id=target, type="reservation_cancelled", title="Reservation cancelled", body=f"The reservation for {reservation.food.title} was cancelled.", route=f"/reservations/{reservation.id}"))
    audit(db, user.id, "reservation.cancelled", "reservation", reservation.id, request.state.request_id)
    existing_events = list(
        db.scalars(
            select(ReservationEvent)
            .where(ReservationEvent.reservation_id == reservation.id, ReservationEvent.id != event.id)
            .order_by(ReservationEvent.occurred_at)
        ).all()
    )
    db.commit()
    return reservation_detail(reservation, [*existing_events, event], False)
