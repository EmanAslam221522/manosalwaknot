from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from app.domain import distance_km
from app.models import FoodStatus

UNVERIFIED = "unverified_organization"
INACTIVE = "inactive_organization"
INSUFFICIENT_CAPACITY = "insufficient_capacity"
EXPIRED_FOOD = "expired_food"
INCOMPATIBLE_PICKUP_WINDOW = "incompatible_pickup_window"
NOT_PUBLISHED = "food_not_published"
NO_SERVINGS = "no_servings_available"
OWN_LISTING = "own_listing"
OUT_OF_RANGE = "outside_service_distance"
INCOMPATIBLE_CATEGORY = "incompatible_category"
MISSING_PROFILE = "missing_organization_profile"
NOT_ORGANIZATION = "not_an_organization"


@dataclass(frozen=True)
class FoodFacts:
    id: UUID
    provider_id: UUID
    status: FoodStatus
    servings_available: int
    expires_at: datetime
    pickup_start: datetime
    pickup_end: datetime
    category_id: UUID
    latitude: float
    longitude: float


@dataclass(frozen=True)
class OrganizationFacts:
    user_id: UUID
    display_name: str
    is_active_user: bool
    deleted: bool
    is_verified: bool
    has_organization_role: bool
    verification_approved: bool
    profile_present: bool
    profile_active: bool
    daily_capacity: int
    remaining_capacity: int
    accepted_category_ids: frozenset[UUID]
    pickup_window_start: time
    pickup_window_end: time
    max_distance_km: float
    people_served: int
    latitude: float
    longitude: float


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reasons: tuple[str, ...]
    distance_km: float | None
    overlap_minutes: int


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def pickup_window_overlap_minutes(
    food_start: datetime,
    food_end: datetime,
    org_start: time,
    org_end: time,
) -> int:
    if food_end <= food_start:
        return 0
    start = _to_utc(food_start)
    end = _to_utc(food_end)
    total = 0
    day = (start - timedelta(days=1)).date() if org_end <= org_start else start.date()
    last_day = end.date()
    while day <= last_day:
        window_start = datetime.combine(day, org_start, tzinfo=UTC)
        if org_end <= org_start:
            window_end = datetime.combine(day + timedelta(days=1), org_end, tzinfo=UTC)
        else:
            window_end = datetime.combine(day, org_end, tzinfo=UTC)
        overlap_start = max(start, window_start)
        overlap_end = min(end, window_end)
        if overlap_end > overlap_start:
            total += int((overlap_end - overlap_start).total_seconds() // 60)
        day += timedelta(days=1)
    return total


def evaluate_eligibility(
    food: FoodFacts,
    org: OrganizationFacts,
    now: datetime,
) -> EligibilityResult:
    reasons: list[str] = []
    distance: float | None = None
    overlap = 0

    if food.status != FoodStatus.PUBLISHED:
        reasons.append(NOT_PUBLISHED)
    if food.expires_at <= now or food.pickup_end <= now:
        reasons.append(EXPIRED_FOOD)
    if food.servings_available <= 0:
        reasons.append(NO_SERVINGS)
    if org.user_id == food.provider_id:
        reasons.append(OWN_LISTING)
    if not org.has_organization_role:
        reasons.append(NOT_ORGANIZATION)
    if not org.profile_present:
        reasons.append(MISSING_PROFILE)
    if not org.is_active_user or org.deleted or not org.profile_active:
        reasons.append(INACTIVE)
    if not org.is_verified or not org.verification_approved:
        reasons.append(UNVERIFIED)
    if org.remaining_capacity < 1:
        reasons.append(INSUFFICIENT_CAPACITY)
    if org.accepted_category_ids and food.category_id not in org.accepted_category_ids:
        reasons.append(INCOMPATIBLE_CATEGORY)

    if org.profile_present:
        distance = distance_km(
            food.latitude,
            food.longitude,
            Decimal(str(org.latitude)),
            Decimal(str(org.longitude)),
        )
        if distance > org.max_distance_km:
            reasons.append(OUT_OF_RANGE)
        overlap = pickup_window_overlap_minutes(
            food.pickup_start,
            food.pickup_end,
            org.pickup_window_start,
            org.pickup_window_end,
        )
        if overlap <= 0:
            reasons.append(INCOMPATIBLE_PICKUP_WINDOW)

    unique = tuple(dict.fromkeys(reasons))
    return EligibilityResult(
        eligible=len(unique) == 0,
        reasons=unique,
        distance_km=distance,
        overlap_minutes=overlap,
    )
