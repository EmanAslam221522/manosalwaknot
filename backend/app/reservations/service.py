from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.domain import audit
from app.models import (
    FoodListing,
    FoodStatus,
    Notification,
    Reservation,
    ReservationEvent,
    ReservationStatus,
    User,
)

ACTIVE_STATES = {
    ReservationStatus.PENDING,
    ReservationStatus.CONFIRMED,
    ReservationStatus.READY,
}


def create_reservation(
    db: Session,
    *,
    food_listing_id: UUID,
    recipient: User,
    quantity: int,
    request_id: str,
    actor: User,
) -> tuple[Reservation, ReservationEvent]:
    food = db.scalar(
        select(FoodListing)
        .options(selectinload(FoodListing.provider), selectinload(FoodListing.location))
        .where(FoodListing.id == food_listing_id)
        .with_for_update()
    )
    now = datetime.now(UTC)
    if food is None or food.status != FoodStatus.PUBLISHED:
        raise ApiError(404, "FOOD_NOT_AVAILABLE", "This food is no longer available.")
    if food.provider_id == recipient.id:
        raise ApiError(409, "OWN_LISTING_RESERVATION", "You cannot reserve your own listing.")
    if food.pickup_end <= now or food.expires_at <= now:
        raise ApiError(409, "FOOD_EXPIRED", "This food is no longer available.")
    if quantity > food.servings_available:
        raise ApiError(
            409,
            "RESERVATION_QUANTITY_UNAVAILABLE",
            "The requested quantity is no longer available.",
        )
    duplicate = db.scalar(
        select(Reservation.id).where(
            Reservation.food_listing_id == food.id,
            Reservation.recipient_id == recipient.id,
            Reservation.status.in_(ACTIVE_STATES),
        )
    )
    if duplicate:
        raise ApiError(
            409,
            "ACTIVE_RESERVATION_EXISTS",
            "You already have an active reservation for this listing.",
        )
    food.servings_available -= quantity
    reservation = Reservation(
        recipient_id=recipient.id,
        food_listing_id=food.id,
        quantity=quantity,
        status=ReservationStatus.CONFIRMED,
        pickup_address=food.location.address,
        handover_instructions=food.location.pickup_instructions,
    )
    reservation.food = food
    db.add(reservation)
    db.flush()
    event = ReservationEvent(
        reservation_id=reservation.id,
        actor_id=actor.id,
        new_state=ReservationStatus.CONFIRMED,
        request_id=request_id,
        actor_label=actor.display_name,
    )
    db.add(event)
    db.flush()
    db.add(
        Notification(
            user_id=food.provider_id,
            type="reservation_confirmed",
            title="New reservation",
            body=f"{quantity} servings of {food.title} were reserved.",
            route=f"/reservations/{reservation.id}",
        )
    )
    if actor.id != recipient.id:
        db.add(
            Notification(
                user_id=recipient.id,
                type="reservation_confirmed",
                title="Food allocated",
                body=f"{quantity} servings of {food.title} were reserved for your organization.",
                route=f"/reservations/{reservation.id}",
            )
        )
    audit(
        db,
        actor.id,
        "reservation.created",
        "reservation",
        reservation.id,
        request_id,
        {"quantity": quantity},
    )
    return reservation, event
