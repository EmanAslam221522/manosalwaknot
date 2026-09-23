from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.domain import audit, pagination
from app.models import DeliveryEvent, DeliveryStatus, DeliveryTask, FoodListing, Notification, Reservation, ReservationStatus, Role, User
from app.schemas import CoordinateOut, DeliveryDetailOut, DeliveryEventOut, DeliveryPage, DeliveryPointOut, DeliverySummaryOut, DeliveryTransitionIn

router = APIRouter(prefix="/deliveries", tags=["deliveries"])

NEXT_STATUS = {
    DeliveryStatus.ACCEPTED: DeliveryStatus.EN_ROUTE_TO_PICKUP,
    DeliveryStatus.EN_ROUTE_TO_PICKUP: DeliveryStatus.ARRIVED_AT_PICKUP,
    DeliveryStatus.ARRIVED_AT_PICKUP: DeliveryStatus.PICKED_UP,
    DeliveryStatus.PICKED_UP: DeliveryStatus.EN_ROUTE_TO_DROPOFF,
    DeliveryStatus.EN_ROUTE_TO_DROPOFF: DeliveryStatus.DELIVERED,
    DeliveryStatus.DELIVERED: DeliveryStatus.COMPLETED,
}
ACTIVE = {DeliveryStatus.ACCEPTED, DeliveryStatus.EN_ROUTE_TO_PICKUP, DeliveryStatus.ARRIVED_AT_PICKUP, DeliveryStatus.PICKED_UP, DeliveryStatus.EN_ROUTE_TO_DROPOFF, DeliveryStatus.DELIVERED}


def load_task():
    return selectinload(DeliveryTask.reservation).selectinload(Reservation.food).selectinload(FoodListing.location), selectinload(DeliveryTask.reservation).selectinload(Reservation.food).selectinload(FoodListing.provider)


def summary(task: DeliveryTask) -> DeliverySummaryOut:
    food = task.reservation.food
    return DeliverySummaryOut(id=task.id, status=task.status, food_title=food.title, servings=task.reservation.quantity, pickup_area=task.pickup_area, dropoff_area=task.dropoff_area, pickup_start=food.pickup_start, pickup_end=food.pickup_end, distance_km=None, updated_at=task.updated_at)


def detail(task: DeliveryTask, db: Session, exact: bool) -> DeliveryDetailOut:
    food, location = task.reservation.food, task.reservation.food.location
    events = db.scalars(select(DeliveryEvent).where(DeliveryEvent.delivery_id == task.id).order_by(DeliveryEvent.occurred_at)).all()
    next_status = NEXT_STATUS.get(task.status)
    return DeliveryDetailOut(**summary(task).model_dump(), pickup=DeliveryPointOut(area=task.pickup_area, address=location.address if exact else None, coordinate=CoordinateOut(latitude=float(food.latitude), longitude=float(food.longitude)) if exact else None, instructions=location.pickup_instructions if exact else None), dropoff=DeliveryPointOut(area=task.dropoff_area, address=task.dropoff_address if exact else None, coordinate=CoordinateOut(latitude=float(task.dropoff_latitude), longitude=float(task.dropoff_longitude)) if exact and task.dropoff_latitude is not None and task.dropoff_longitude is not None else None, instructions=task.dropoff_instructions if exact else None), allowed_transitions=[next_status] if next_status else [], events=[DeliveryEventOut(id=event.id, previous_state=event.previous_state, new_state=event.new_state, actor_label=event.actor_label, occurred_at=event.occurred_at) for event in events])


@router.get("/available", response_model=DeliveryPage)
def available_deliveries(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), _: User = Depends(require_roles(Role.VOLUNTEER)), db: Session = Depends(get_db)) -> DeliveryPage:
    condition = DeliveryTask.status == DeliveryStatus.AVAILABLE
    total = db.scalar(select(func.count()).select_from(DeliveryTask).where(condition)) or 0
    tasks = db.scalars(select(DeliveryTask).options(*load_task()).where(condition).order_by(DeliveryTask.created_at).offset((page - 1) * page_size).limit(page_size)).all()
    return DeliveryPage(items=[summary(task) for task in tasks], meta=pagination(total, page, page_size))


@router.get("", response_model=DeliveryPage)
def my_deliveries(status_filter: str = Query("active", alias="status", pattern="^(active|completed)$"), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(require_roles(Role.VOLUNTEER)), db: Session = Depends(get_db)) -> DeliveryPage:
    statuses = ACTIVE if status_filter == "active" else {DeliveryStatus.COMPLETED, DeliveryStatus.CANCELLED}
    filters = [DeliveryTask.volunteer_id == user.id, DeliveryTask.status.in_(statuses)]
    total = db.scalar(select(func.count()).select_from(DeliveryTask).where(*filters)) or 0
    tasks = db.scalars(select(DeliveryTask).options(*load_task()).where(*filters).order_by(DeliveryTask.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return DeliveryPage(items=[summary(task) for task in tasks], meta=pagination(total, page, page_size))


@router.post("", response_model=DeliveryDetailOut, status_code=status.HTTP_201_CREATED)
def create_delivery(payload: dict[str, object], request: Request, user: User = Depends(require_roles(Role.FOOD_PROVIDER, Role.ORGANIZATION)), db: Session = Depends(get_db)) -> DeliveryDetailOut:
    try:
        reservation_id = UUID(str(payload["reservation_id"]))
        dropoff_area = str(payload["dropoff_area"])
    except (KeyError, ValueError) as exc:
        raise ApiError(422, "INVALID_DELIVERY", "Reservation and drop-off area are required.") from exc
    reservation = db.scalar(select(Reservation).options(selectinload(Reservation.food).selectinload(FoodListing.location), selectinload(Reservation.food).selectinload(FoodListing.provider)).where(Reservation.id == reservation_id))
    if reservation is None or reservation.food.provider_id != user.id:
        raise ApiError(404, "RESERVATION_NOT_FOUND", "This reservation was not found.")
    if reservation.status not in {ReservationStatus.CONFIRMED, ReservationStatus.READY}:
        raise ApiError(409, "DELIVERY_NOT_AVAILABLE", "A delivery cannot be created for this reservation.")
    if db.scalar(select(DeliveryTask.id).where(DeliveryTask.reservation_id == reservation.id)):
        raise ApiError(409, "DELIVERY_ALREADY_EXISTS", "A delivery already exists for this reservation.")
    task = DeliveryTask(reservation_id=reservation.id, pickup_area=reservation.food.area, dropoff_area=dropoff_area, dropoff_address=str(payload.get("dropoff_address")) if payload.get("dropoff_address") else None, dropoff_latitude=float(payload["dropoff_latitude"]) if payload.get("dropoff_latitude") is not None else None, dropoff_longitude=float(payload["dropoff_longitude"]) if payload.get("dropoff_longitude") is not None else None, dropoff_instructions=str(payload.get("dropoff_instructions")) if payload.get("dropoff_instructions") else None)
    db.add(task)
    db.flush()
    db.add(DeliveryEvent(delivery_id=task.id, actor_id=user.id, new_state=DeliveryStatus.AVAILABLE, request_id=request.state.request_id, actor_label=user.display_name))
    audit(db, user.id, "delivery.created", "delivery_task", task.id, request.state.request_id)
    db.commit()
    return detail(task, db, True)


@router.get("/{delivery_id}", response_model=DeliveryDetailOut)
def get_delivery(delivery_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> DeliveryDetailOut:
    task = db.scalar(select(DeliveryTask).options(*load_task()).where(DeliveryTask.id == delivery_id))
    roles = {entry.role for entry in user.roles}
    if task is None or (task.volunteer_id != user.id and user.id not in {task.reservation.recipient_id, task.reservation.food.provider_id} and not (task.status == DeliveryStatus.AVAILABLE and Role.VOLUNTEER in roles) and not roles.intersection({Role.ADMIN, Role.SUPER_ADMIN})):
        raise ApiError(404, "DELIVERY_NOT_FOUND", "This delivery task was not found.")
    exact = task.volunteer_id == user.id or user.id in {task.reservation.recipient_id, task.reservation.food.provider_id} or bool(roles.intersection({Role.ADMIN, Role.SUPER_ADMIN}))
    return detail(task, db, exact)


@router.post("/{delivery_id}/accept", response_model=DeliveryDetailOut)
def accept_delivery(delivery_id: UUID, request: Request, user: User = Depends(require_roles(Role.VOLUNTEER)), db: Session = Depends(get_db)) -> DeliveryDetailOut:
    task = db.scalar(select(DeliveryTask).options(*load_task()).where(DeliveryTask.id == delivery_id).with_for_update())
    if task is None:
        raise ApiError(404, "DELIVERY_NOT_FOUND", "This delivery task was not found.")
    if task.status != DeliveryStatus.AVAILABLE or task.volunteer_id is not None:
        raise ApiError(409, "DELIVERY_ALREADY_ACCEPTED", "This delivery task is no longer available.")
    task.volunteer_id, task.status = user.id, DeliveryStatus.ACCEPTED
    db.add(DeliveryEvent(delivery_id=task.id, actor_id=user.id, previous_state=DeliveryStatus.AVAILABLE, new_state=DeliveryStatus.ACCEPTED, request_id=request.state.request_id, actor_label=user.display_name))
    audit(db, user.id, "delivery.accepted", "delivery_task", task.id, request.state.request_id)
    db.commit()
    return detail(task, db, True)


@router.post("/{delivery_id}/transitions", response_model=DeliveryDetailOut)
def transition_delivery(delivery_id: UUID, payload: DeliveryTransitionIn, request: Request, user: User = Depends(require_roles(Role.VOLUNTEER)), db: Session = Depends(get_db)) -> DeliveryDetailOut:
    task = db.scalar(select(DeliveryTask).options(*load_task()).where(DeliveryTask.id == delivery_id).with_for_update())
    if task is None or task.volunteer_id != user.id:
        raise ApiError(404, "DELIVERY_NOT_FOUND", "This delivery task was not found.")
    if NEXT_STATUS.get(task.status) != payload.status:
        raise ApiError(409, "INVALID_DELIVERY_TRANSITION", "That delivery update is not allowed.")
    previous, task.status = task.status, payload.status
    if payload.status == DeliveryStatus.PICKED_UP:
        task.reservation.status = ReservationStatus.PICKED_UP
    elif payload.status == DeliveryStatus.DELIVERED:
        task.reservation.status = ReservationStatus.DELIVERED
    elif payload.status == DeliveryStatus.COMPLETED:
        task.reservation.status = ReservationStatus.COMPLETED
    db.add(DeliveryEvent(delivery_id=task.id, actor_id=user.id, previous_state=previous, new_state=payload.status, request_id=request.state.request_id, actor_label=user.display_name))
    db.add(Notification(user_id=task.reservation.recipient_id, type="delivery_updated", title="Delivery updated", body=f"Delivery status: {payload.status.value.replace('_', ' ').title()}.", route=f"/deliveries/{task.id}"))
    audit(db, user.id, "delivery.transitioned", "delivery_task", task.id, request.state.request_id, {"from": previous.value, "to": payload.status.value})
    db.commit()
    return detail(task, db, True)
