from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from geoalchemy2 import Geography
from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.domain import audit, can_view_exact_food, food_detail, food_summary, pagination
from app.models import FoodCategory, FoodListing, FoodStatus, Location, Role, User
from app.schemas import FoodDetailOut, FoodDraftIn, FoodPage

router = APIRouter(prefix="/food", tags=["food"])


def food_load() -> tuple[object, object]:
    return selectinload(FoodListing.provider), selectinload(FoodListing.location)


@router.get("", response_model=FoodPage)
def list_food(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, alias="q", max_length=120),
    city: str | None = Query(None, max_length=120),
    area: str | None = Query(None, max_length=160),
    price: str | None = Query(None, pattern="^(FREE|DISCOUNTED)$"),
    category_id: UUID | None = None,
    dietary: str | None = Query(None, alias="dietary_type", max_length=80),
    pickup_after: datetime | None = None,
    pickup_before: datetime | None = None,
    delivery_available: bool | None = None,
    ending_soon: bool | None = None,
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    radius_km: float | None = Query(None, gt=0, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
) -> FoodPage:
    if (lat is None) != (lng is None) or (radius_km is not None and lat is None):
        raise ApiError(422, "INVALID_LOCATION_FILTER", "Latitude and longitude must be provided together.")
    now = datetime.now(UTC)
    filters = [
        FoodListing.status == FoodStatus.PUBLISHED,
        FoodListing.servings_available > 0,
        FoodListing.expires_at > now,
    ]
    if search:
        term = f"%{search}%"
        filters.append(
            or_(
                FoodListing.title.ilike(term),
                FoodListing.description.ilike(term),
                FoodListing.area.ilike(term),
            )
        )
    if city:
        filters.append(FoodListing.city.ilike(city))
    if area:
        filters.append(FoodListing.area.ilike(area))
    if price == "FREE":
        filters.append(FoodListing.is_free.is_(True))
    elif price == "DISCOUNTED":
        filters.append(FoodListing.is_free.is_(False))
    if category_id:
        filters.append(FoodListing.category_id == category_id)
    if dietary:
        filters.append(FoodListing.dietary_information.contains([dietary]))
    if pickup_after:
        filters.append(FoodListing.pickup_end >= pickup_after)
    if pickup_before:
        filters.append(FoodListing.pickup_start <= pickup_before)
    if delivery_available is not None:
        filters.append(FoodListing.delivery_available == delivery_available)
    if ending_soon:
        filters.append(FoodListing.pickup_end <= now + timedelta(hours=2))
    if radius_km is not None and lat is not None and lng is not None:
        point = cast(
            func.ST_SetSRID(func.ST_MakePoint(FoodListing.longitude, FoodListing.latitude), 4326),
            Geography,
        )
        origin = cast(func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326), Geography)
        filters.append(func.ST_DWithin(point, origin, radius_km * 1000))
    total = db.scalar(select(func.count()).select_from(FoodListing).where(*filters)) or 0
    foods = db.scalars(
        select(FoodListing)
        .options(*food_load())
        .where(*filters)
        .order_by(FoodListing.pickup_end)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return FoodPage(
        items=[food_summary(food, lat, lng) for food in foods],
        meta=pagination(total, page, page_size),
    )


@router.get("/categories")
def categories(db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict[str, object]]:
    rows = db.scalars(select(FoodCategory).where(FoodCategory.is_active.is_(True)).order_by(FoodCategory.name)).all()
    return [{"id": item.id, "name": item.name} for item in rows]


@router.post("", response_model=FoodDetailOut, status_code=status.HTTP_201_CREATED)
def create_food(payload: FoodDraftIn, request: Request, user: User = Depends(require_roles(Role.FOOD_PROVIDER, Role.ORGANIZATION)), db: Session = Depends(get_db)) -> FoodDetailOut:
    location = db.scalar(select(Location).where(Location.id == payload.location_id, Location.owner_id == user.id, Location.is_active.is_(True)))
    if location is None:
        raise ApiError(404, "LOCATION_NOT_FOUND", "The selected pickup location was not found.")
    if db.get(FoodCategory, payload.category_id) is None:
        raise ApiError(422, "CATEGORY_NOT_FOUND", "Choose a valid food category.")
    food = FoodListing(provider_id=user.id, category_id=payload.category_id, location_id=location.id, title=payload.title, description=payload.description, quantity=payload.quantity, servings_total=payload.servings, servings_available=payload.servings, unit=payload.unit, price=payload.price or 0, is_free=payload.is_free, pickup_start=payload.pickup_start, pickup_end=payload.pickup_end, expires_at=payload.pickup_end, city=location.city, area=location.area, latitude=location.latitude, longitude=location.longitude, ingredients=payload.ingredients, allergens=payload.allergens, dietary_information=payload.dietary_information, storage_information=payload.storage_information, preparation_time=payload.preparation_time, provider_safety_confirmed=payload.provider_safety_confirmed)
    db.add(food)
    db.flush()
    audit(db, user.id, "food.created", "food_listing", food.id, request.state.request_id)
    db.commit()
    return food_detail(food, True)


@router.get("/{food_id}", response_model=FoodDetailOut)
def get_food(food_id: UUID, lat: float | None = None, lng: float | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)) -> FoodDetailOut:
    food = db.scalar(select(FoodListing).options(*food_load()).where(FoodListing.id == food_id))
    if food is None:
        raise ApiError(404, "FOOD_NOT_FOUND", "This food listing was not found.")
    roles = {entry.role for entry in user.roles}
    if food.status == FoodStatus.DRAFT and food.provider_id != user.id and not roles.intersection({Role.ADMIN, Role.SUPER_ADMIN}):
        raise ApiError(404, "FOOD_NOT_FOUND", "This food listing was not found.")
    return food_detail(food, can_view_exact_food(user, food, db), lat, lng)


@router.post("/{food_id}/publish", response_model=FoodDetailOut)
def publish_food(food_id: UUID, request: Request, user: User = Depends(require_roles(Role.FOOD_PROVIDER, Role.ORGANIZATION)), db: Session = Depends(get_db)) -> FoodDetailOut:
    food = db.scalar(select(FoodListing).options(*food_load()).where(FoodListing.id == food_id, FoodListing.provider_id == user.id).with_for_update())
    if food is None:
        raise ApiError(404, "FOOD_NOT_FOUND", "This food listing was not found.")
    if food.status != FoodStatus.DRAFT:
        raise ApiError(409, "INVALID_FOOD_TRANSITION", "Only draft listings can be published.")
    if food.pickup_end <= datetime.now(UTC):
        raise ApiError(409, "FOOD_WINDOW_EXPIRED", "Update the pickup window before publishing.")
    food.status = FoodStatus.PUBLISHED
    audit(db, user.id, "food.published", "food_listing", food.id, request.state.request_id)
    db.commit()
    return food_detail(food, True)
