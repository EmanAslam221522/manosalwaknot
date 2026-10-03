from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.matching.eligibility import EligibilityResult, FoodFacts, OrganizationFacts
from app.matching.schemas import MatchingWeights, ScoreBreakdownOut


@dataclass(frozen=True)
class ScoreInputs:
    distance_km: float
    max_distance_km: float
    remaining_capacity: int
    servings_available: int
    overlap_minutes: int
    food_window_minutes: int
    people_served: int
    verified: bool
    profile_complete: bool


def configured_weights() -> MatchingWeights:
    settings = get_settings()
    return MatchingWeights(
        location=settings.match_weight_location,
        capacity=settings.match_weight_capacity,
        timing=settings.match_weight_timing,
        demand=settings.match_weight_demand,
        readiness=settings.match_weight_readiness,
    )


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def location_score(distance_km: float, max_distance_km: float) -> float:
    if max_distance_km <= 0:
        return 0.0
    return _clamp(100.0 * (1.0 - (distance_km / max_distance_km)))


def capacity_score(remaining_capacity: int, servings_available: int) -> float:
    need = max(servings_available, 1)
    if remaining_capacity >= need:
        return 100.0
    return _clamp(100.0 * remaining_capacity / need)


def timing_score(overlap_minutes: int, food_window_minutes: int) -> float:
    duration = max(food_window_minutes, 1)
    return _clamp(100.0 * overlap_minutes / duration)


def demand_score(people_served: int, servings_available: int) -> float:
    baseline = max(servings_available, 1)
    return _clamp(100.0 * min(people_served, baseline * 4) / (baseline * 4))


def readiness_score(verified: bool, profile_complete: bool) -> float:
    if verified and profile_complete:
        return 100.0
    if verified:
        return 50.0
    return 0.0


def score_match(inputs: ScoreInputs, weights: MatchingWeights | None = None) -> ScoreBreakdownOut:
    chosen = weights or configured_weights()
    location = location_score(inputs.distance_km, inputs.max_distance_km)
    capacity = capacity_score(inputs.remaining_capacity, inputs.servings_available)
    timing = timing_score(inputs.overlap_minutes, inputs.food_window_minutes)
    demand = demand_score(inputs.people_served, inputs.servings_available)
    readiness = readiness_score(inputs.verified, inputs.profile_complete)
    total = _clamp(
        location * chosen.location
        + capacity * chosen.capacity
        + timing * chosen.timing
        + demand * chosen.demand
        + readiness * chosen.readiness
    )
    return ScoreBreakdownOut(
        location=location,
        capacity=capacity,
        timing=timing,
        demand=demand,
        readiness=readiness,
        total=total,
        weights=chosen,
    )


def score_from_eligibility(
    food: FoodFacts,
    org: OrganizationFacts,
    eligibility: EligibilityResult,
    weights: MatchingWeights | None = None,
) -> ScoreBreakdownOut:
    window_minutes = max(int((food.pickup_end - food.pickup_start).total_seconds() // 60), 1)
    return score_match(
        ScoreInputs(
            distance_km=eligibility.distance_km or 0.0,
            max_distance_km=org.max_distance_km,
            remaining_capacity=org.remaining_capacity,
            servings_available=food.servings_available,
            overlap_minutes=eligibility.overlap_minutes,
            food_window_minutes=window_minutes,
            people_served=org.people_served,
            verified=org.is_verified and org.verification_approved,
            profile_complete=org.profile_present and org.profile_active,
        ),
        weights,
    )


def explanation_from_evidence(
    organization_name: str,
    organization_type: str,
    distance_km: float,
    remaining_capacity: int,
    overlap_minutes: int,
    people_served: int,
) -> str:
    label = organization_type.replace("_", " ").title()
    return (
        f"{organization_name} is a verified {label} {distance_km} km from pickup, "
        f"with {remaining_capacity} servings of remaining daily capacity, "
        f"{overlap_minutes} minutes of pickup-window overlap, "
        f"and reported demand of {people_served} people served."
    )
