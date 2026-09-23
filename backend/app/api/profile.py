from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.database import get_db
from app.core.errors import ApiError
from app.domain import user_out
from app.models import Location, User
from app.schemas import LocationPreference, UserOut

router = APIRouter(prefix="/users", tags=["profiles"])


@router.put("/me/location-preference", response_model=UserOut)
def update_location_preference(payload: LocationPreference, user: User = Depends(current_user), db: Session = Depends(get_db)) -> UserOut:
    user.city, user.area = payload.city, payload.area
    db.commit()
    return user_out(user)


@router.get("/me/locations")
def list_locations(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.scalars(select(Location).where(Location.owner_id == user.id, Location.is_active.is_(True)).order_by(Location.created_at.desc())).all()
    return [{"id": row.id, "city": row.city, "area": row.area, "address": row.address, "latitude": float(row.latitude), "longitude": float(row.longitude), "pickup_instructions": row.pickup_instructions} for row in rows]


@router.post("/me/locations")
def create_location(payload: dict[str, object], user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    required = ("city", "area", "address", "latitude", "longitude")
    if any(key not in payload for key in required):
        raise ApiError(422, "INVALID_LOCATION", "City, area, address, latitude, and longitude are required.")
    try:
        location = Location(owner_id=user.id, city=str(payload["city"]), area=str(payload["area"]), address=str(payload["address"]), latitude=float(payload["latitude"]), longitude=float(payload["longitude"]), pickup_instructions=str(payload["pickup_instructions"]) if payload.get("pickup_instructions") else None)
    except (TypeError, ValueError) as exc:
        raise ApiError(422, "INVALID_LOCATION", "The pickup location is invalid.") from exc
    db.add(location)
    db.commit()
    db.refresh(location)
    return {"id": location.id, "city": location.city, "area": location.area, "address": location.address, "latitude": float(location.latitude), "longitude": float(location.longitude), "pickup_instructions": location.pickup_instructions}
