from __future__ import annotations

from datetime import time
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import FoodMatchStatus, OrganizationType
from app.schemas import StrictModel


class MatchingWeights(BaseModel):
    location: float
    capacity: float
    timing: float
    demand: float
    readiness: float


class ScoreBreakdownOut(BaseModel):
    location: float
    capacity: float
    timing: float
    demand: float
    readiness: float
    total: float
    weights: MatchingWeights


class MatchEvidenceOut(BaseModel):
    distance_km: float
    remaining_capacity: int
    daily_capacity: int
    overlap_minutes: int
    people_served: int
    organization_verified: bool
    servings_available: int
    organization_type: OrganizationType


class OrganizationProfileIn(StrictModel):
    location_id: UUID
    organization_type: OrganizationType
    daily_capacity: int = Field(gt=0, le=100000)
    people_served: int = Field(ge=0, le=1000000)
    accepted_category_ids: list[UUID] = Field(default_factory=list, max_length=50)
    pickup_window_start: time
    pickup_window_end: time
    max_distance_km: float = Field(gt=0, le=200, allow_inf_nan=False)


class OrganizationProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    location_id: UUID
    organization_type: OrganizationType
    daily_capacity: int
    people_served: int
    accepted_category_ids: list[UUID]
    pickup_window_start: time
    pickup_window_end: time
    max_distance_km: float
    is_active: bool
    city: str
    area: str


class MatchAcceptIn(StrictModel):
    quantity: int = Field(gt=0, le=10000)


class FoodMatchOut(BaseModel):
    id: UUID
    food_listing_id: UUID
    organization_id: UUID
    organization_name: str
    organization_type: OrganizationType
    status: FoodMatchStatus
    score: float
    score_breakdown: ScoreBreakdownOut
    evidence: MatchEvidenceOut
    explanation: str
    quantity_snapshot: int
    reservation_id: UUID | None
    city: str
    area: str


class FoodMatchPage(BaseModel):
    items: list[FoodMatchOut]
    food_listing_id: UUID
    servings_available: int
