from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.domain import audit
from app.matching.eligibility import FoodFacts, OrganizationFacts, evaluate_eligibility
from app.matching.schemas import (
    FoodMatchOut,
    FoodMatchPage,
    MatchEvidenceOut,
    OrganizationProfileIn,
    OrganizationProfileOut,
    ScoreBreakdownOut,
)
from app.matching.scoring import explanation_from_evidence, score_from_eligibility
from app.models import (
    FoodCategory,
    FoodListing,
    FoodMatch,
    FoodMatchStatus,
    FoodStatus,
    Location,
    OrganizationProfile,
    Reservation,
    Role,
    User,
    UserRole,
    VerificationRequest,
    VerificationStatus,
    VerificationType,
)
from app.reservations.service import ACTIVE_STATES, create_reservation


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _day_start(now: datetime) -> datetime:
    return _to_utc(now).replace(hour=0, minute=0, second=0, microsecond=0)


def remaining_daily_capacity(
    db: Session,
    organization_id: UUID,
    daily_capacity: int,
    now: datetime,
) -> int:
    used = db.scalar(
        select(func.coalesce(func.sum(Reservation.quantity), 0)).where(
            Reservation.recipient_id == organization_id,
            Reservation.status.in_(ACTIVE_STATES),
            Reservation.created_at >= _day_start(now),
        )
    )
    consumed = int(used or 0)
    return max(0, daily_capacity - consumed)


def _food_facts(food: FoodListing) -> FoodFacts:
    return FoodFacts(
        id=food.id,
        provider_id=food.provider_id,
        status=food.status,
        servings_available=food.servings_available,
        expires_at=food.expires_at,
        pickup_start=food.pickup_start,
        pickup_end=food.pickup_end,
        category_id=food.category_id,
        latitude=float(food.latitude),
        longitude=float(food.longitude),
    )


def _org_facts(
    db: Session,
    user: User,
    profile: OrganizationProfile,
    now: datetime,
    verification_approved: bool,
) -> OrganizationFacts:
    roles = {entry.role for entry in user.roles}
    accepted = frozenset(UUID(value) for value in profile.accepted_category_ids)
    return OrganizationFacts(
        user_id=user.id,
        display_name=user.display_name,
        is_active_user=user.is_active,
        deleted=user.deleted_at is not None,
        is_verified=user.is_verified,
        has_organization_role=Role.ORGANIZATION in roles,
        verification_approved=verification_approved,
        profile_present=True,
        profile_active=profile.is_active,
        daily_capacity=profile.daily_capacity,
        remaining_capacity=remaining_daily_capacity(db, user.id, profile.daily_capacity, now),
        accepted_category_ids=accepted,
        pickup_window_start=profile.pickup_window_start,
        pickup_window_end=profile.pickup_window_end,
        max_distance_km=float(profile.max_distance_km),
        people_served=profile.people_served,
        latitude=float(profile.location.latitude),
        longitude=float(profile.location.longitude),
    )


def _role_values(user: User) -> set[Role]:
    return {entry.role for entry in user.roles}


def _can_manage_listing(user: User, food: FoodListing) -> bool:
    roles = _role_values(user)
    return food.provider_id == user.id or bool(roles.intersection({Role.ADMIN, Role.SUPER_ADMIN}))


def _can_access_match(user: User, match: FoodMatch, food: FoodListing) -> bool:
    roles = _role_values(user)
    return (
        user.id in {food.provider_id, match.organization_id}
        or bool(roles.intersection({Role.ADMIN, Role.SUPER_ADMIN}))
    )


def _match_out(match: FoodMatch) -> FoodMatchOut:
    breakdown = ScoreBreakdownOut.model_validate(match.score_breakdown)
    evidence = MatchEvidenceOut.model_validate(match.evidence)
    location = match.profile.location
    return FoodMatchOut(
        id=match.id,
        food_listing_id=match.food_listing_id,
        organization_id=match.organization_id,
        organization_name=match.organization.display_name,
        organization_type=evidence.organization_type,
        status=match.status,
        score=float(match.score),
        score_breakdown=breakdown,
        evidence=evidence,
        explanation=match.explanation,
        quantity_snapshot=match.quantity_snapshot,
        reservation_id=match.reservation_id,
        city=location.city,
        area=location.area,
    )


def profile_out(profile: OrganizationProfile) -> OrganizationProfileOut:
    return OrganizationProfileOut(
        id=profile.id,
        user_id=profile.user_id,
        location_id=profile.location_id,
        organization_type=profile.organization_type,
        daily_capacity=profile.daily_capacity,
        people_served=profile.people_served,
        accepted_category_ids=[UUID(value) for value in profile.accepted_category_ids],
        pickup_window_start=profile.pickup_window_start,
        pickup_window_end=profile.pickup_window_end,
        max_distance_km=float(profile.max_distance_km),
        is_active=profile.is_active,
        city=profile.location.city,
        area=profile.location.area,
    )


def upsert_organization_profile(
    db: Session,
    user: User,
    payload: OrganizationProfileIn,
    request_id: str,
) -> OrganizationProfile:
    if Role.ORGANIZATION not in _role_values(user):
        raise ApiError(403, "ROLE_REQUIRED", "You are not authorized to perform this action.")
    location = db.scalar(
        select(Location).where(
            Location.id == payload.location_id,
            Location.owner_id == user.id,
            Location.is_active.is_(True),
        )
    )
    if location is None:
        raise ApiError(404, "LOCATION_NOT_FOUND", "The selected pickup location was not found.")
    for category_id in payload.accepted_category_ids:
        if db.get(FoodCategory, category_id) is None:
            raise ApiError(422, "CATEGORY_NOT_FOUND", "Choose a valid food category.")
    stored_categories = [str(item) for item in payload.accepted_category_ids]
    existing = db.scalar(
        select(OrganizationProfile)
        .options(selectinload(OrganizationProfile.location))
        .where(OrganizationProfile.user_id == user.id)
        .with_for_update()
    )
    if existing:
        existing.location_id = location.id
        existing.organization_type = payload.organization_type
        existing.daily_capacity = payload.daily_capacity
        existing.people_served = payload.people_served
        existing.accepted_category_ids = stored_categories
        existing.pickup_window_start = payload.pickup_window_start
        existing.pickup_window_end = payload.pickup_window_end
        existing.max_distance_km = Decimal(str(payload.max_distance_km))
        existing.is_active = True
        existing.location = location
        profile = existing
        action = "organization_profile.updated"
    else:
        profile = OrganizationProfile(
            user_id=user.id,
            location_id=location.id,
            organization_type=payload.organization_type,
            daily_capacity=payload.daily_capacity,
            people_served=payload.people_served,
            accepted_category_ids=stored_categories,
            pickup_window_start=payload.pickup_window_start,
            pickup_window_end=payload.pickup_window_end,
            max_distance_km=Decimal(str(payload.max_distance_km)),
        )
        profile.location = location
        db.add(profile)
        db.flush()
        action = "organization_profile.created"
    audit(db, user.id, action, "organization_profile", profile.id, request_id)
    return profile


def get_own_profile(db: Session, user: User) -> OrganizationProfile:
    profile = db.scalar(
        select(OrganizationProfile)
        .options(selectinload(OrganizationProfile.location))
        .where(OrganizationProfile.user_id == user.id)
    )
    if profile is None:
        raise ApiError(
            404,
            "ORGANIZATION_PROFILE_NOT_FOUND",
            "Set up your organization profile first.",
        )
    return profile


def _lock_food(db: Session, food_id: UUID) -> FoodListing | None:
    return db.scalar(
        select(FoodListing)
        .options(selectinload(FoodListing.provider), selectinload(FoodListing.location))
        .where(FoodListing.id == food_id)
        .with_for_update()
    )


def generate_recommendations(
    db: Session,
    food_id: UUID,
    actor: User,
    request_id: str,
) -> FoodMatchPage:
    food = _lock_food(db, food_id)
    if food is None or not _can_manage_listing(actor, food):
        raise ApiError(404, "FOOD_NOT_FOUND", "This food listing was not found.")
    now = datetime.now(UTC)
    if food.status != FoodStatus.PUBLISHED:
        raise ApiError(
            409,
            "FOOD_NOT_PUBLISHED",
            "Recommendations are only available for published food.",
        )
    if food.expires_at <= now or food.pickup_end <= now:
        for stale in db.scalars(
            select(FoodMatch)
            .where(
                FoodMatch.food_listing_id == food.id,
                FoodMatch.status == FoodMatchStatus.RECOMMENDED,
            )
            .with_for_update()
        ):
            stale.status = FoodMatchStatus.EXPIRED
        audit(db, actor.id, "food_match.expired", "food_listing", food.id, request_id)
        db.commit()
        raise ApiError(409, "FOOD_EXPIRED", "This food is no longer available.")
    if food.servings_available <= 0:
        raise ApiError(
            409,
            "RESERVATION_QUANTITY_UNAVAILABLE",
            "The requested quantity is no longer available.",
        )

    approved_org_ids = set(
        db.scalars(
            select(VerificationRequest.user_id).where(
                VerificationRequest.type == VerificationType.ORGANIZATION,
                VerificationRequest.status == VerificationStatus.APPROVED,
            )
        )
    )
    candidates = db.scalars(
        select(OrganizationProfile)
        .options(
            selectinload(OrganizationProfile.user).selectinload(User.roles),
            selectinload(OrganizationProfile.location),
        )
        .join(User, User.id == OrganizationProfile.user_id)
        .join(UserRole, UserRole.user_id == User.id)
        .where(UserRole.role == Role.ORGANIZATION)
    ).all()

    facts = _food_facts(food)
    eligible_ids: set[UUID] = set()
    ranked: list[FoodMatch] = []
    for profile in candidates:
        org_user = profile.user
        org = _org_facts(db, org_user, profile, now, org_user.id in approved_org_ids)
        result = evaluate_eligibility(facts, org, now)
        if not result.eligible or result.distance_km is None:
            continue
        eligible_ids.add(org_user.id)
        breakdown = score_from_eligibility(facts, org, result)
        evidence = MatchEvidenceOut(
            distance_km=result.distance_km,
            remaining_capacity=org.remaining_capacity,
            daily_capacity=org.daily_capacity,
            overlap_minutes=result.overlap_minutes,
            people_served=org.people_served,
            organization_verified=True,
            servings_available=food.servings_available,
            organization_type=profile.organization_type,
        )
        explanation = explanation_from_evidence(
            org.display_name,
            profile.organization_type.value,
            result.distance_km,
            org.remaining_capacity,
            result.overlap_minutes,
            org.people_served,
        )
        match = db.scalar(
            select(FoodMatch)
            .where(
                FoodMatch.food_listing_id == food.id,
                FoodMatch.organization_id == org_user.id,
            )
            .with_for_update()
        )
        if match and match.status in {FoodMatchStatus.ACCEPTED, FoodMatchStatus.DECLINED}:
            ranked.append(match)
            continue
        if match is None:
            match = FoodMatch(
                food_listing_id=food.id,
                organization_id=org_user.id,
                organization_profile_id=profile.id,
            )
            db.add(match)
        match.organization_profile_id = profile.id
        match.status = FoodMatchStatus.RECOMMENDED
        match.quantity_snapshot = food.servings_available
        match.score = Decimal(str(breakdown.total))
        match.score_breakdown = breakdown.model_dump(mode="json")
        match.evidence = evidence.model_dump(mode="json")
        match.explanation = explanation
        match.organization = org_user
        match.profile = profile
        db.flush()
        ranked.append(match)

    stale_filter = [
        FoodMatch.food_listing_id == food.id,
        FoodMatch.status == FoodMatchStatus.RECOMMENDED,
    ]
    if eligible_ids:
        stale_filter.append(FoodMatch.organization_id.not_in(eligible_ids))
    for previous in db.scalars(select(FoodMatch).where(*stale_filter).with_for_update()):
        if previous.organization_id not in eligible_ids:
            previous.status = FoodMatchStatus.SUPERSEDED

    db.flush()
    visible = [
        item
        for item in ranked
        if item.status == FoodMatchStatus.RECOMMENDED
    ]
    visible.sort(
        key=lambda item: (-float(item.score), item.organization.display_name, str(item.id))
    )
    audit(
        db,
        actor.id,
        "food_match.recommended",
        "food_listing",
        food.id,
        request_id,
        {"count": len(visible)},
    )
    return FoodMatchPage(
        items=[_match_out(item) for item in visible],
        food_listing_id=food.id,
        servings_available=food.servings_available,
    )


def list_recommendations(db: Session, food_id: UUID, actor: User) -> FoodMatchPage:
    food = db.scalar(
        select(FoodListing)
        .options(selectinload(FoodListing.provider), selectinload(FoodListing.location))
        .where(FoodListing.id == food_id)
    )
    if food is None or not _can_manage_listing(actor, food):
        raise ApiError(404, "FOOD_NOT_FOUND", "This food listing was not found.")
    matches = db.scalars(
        select(FoodMatch)
        .options(
            selectinload(FoodMatch.organization),
            selectinload(FoodMatch.profile).selectinload(OrganizationProfile.location),
        )
        .where(
            FoodMatch.food_listing_id == food.id,
            FoodMatch.status == FoodMatchStatus.RECOMMENDED,
        )
        .order_by(FoodMatch.score.desc(), FoodMatch.created_at)
    ).all()
    return FoodMatchPage(
        items=[_match_out(item) for item in matches],
        food_listing_id=food.id,
        servings_available=food.servings_available,
    )


def _load_match_for_update(db: Session, match_id: UUID) -> FoodMatch | None:
    preview = db.get(FoodMatch, match_id)
    if preview is None:
        return None
    _lock_food(db, preview.food_listing_id)
    return db.scalar(
        select(FoodMatch)
        .options(
            selectinload(FoodMatch.organization).selectinload(User.roles),
            selectinload(FoodMatch.profile).selectinload(OrganizationProfile.location),
            selectinload(FoodMatch.food).selectinload(FoodListing.location),
            selectinload(FoodMatch.food).selectinload(FoodListing.provider),
        )
        .where(FoodMatch.id == match_id)
        .with_for_update()
    )


def accept_match(
    db: Session,
    match_id: UUID,
    actor: User,
    quantity: int,
    request_id: str,
) -> FoodMatchOut:
    match = _load_match_for_update(db, match_id)
    if match is None or match.food is None or not _can_access_match(actor, match, match.food):
        raise ApiError(404, "FOOD_MATCH_NOT_FOUND", "This recommendation was not found.")
    if match.status == FoodMatchStatus.ACCEPTED and match.reservation_id is not None:
        return _match_out(match)
    if match.status != FoodMatchStatus.RECOMMENDED:
        raise ApiError(409, "INVALID_MATCH_TRANSITION", "This recommendation cannot be accepted.")

    now = datetime.now(UTC)
    food = match.food
    approved = db.scalar(
        select(VerificationRequest.id).where(
            VerificationRequest.user_id == match.organization_id,
            VerificationRequest.type == VerificationType.ORGANIZATION,
            VerificationRequest.status == VerificationStatus.APPROVED,
        )
    )
    org = _org_facts(db, match.organization, match.profile, now, approved is not None)
    result = evaluate_eligibility(_food_facts(food), org, now)
    if not result.eligible:
        match.status = FoodMatchStatus.SUPERSEDED
        db.commit()
        raise ApiError(
            409,
            "MATCH_NO_LONGER_ELIGIBLE",
            "This organization is no longer eligible for this listing.",
            {"reasons": list(result.reasons)},
        )
    if quantity > org.remaining_capacity:
        raise ApiError(
            409,
            "INSUFFICIENT_ORGANIZATION_CAPACITY",
            "This organization does not have remaining capacity for that quantity.",
        )
    reservation, _event = create_reservation(
        db,
        food_listing_id=food.id,
        recipient=match.organization,
        quantity=quantity,
        request_id=request_id,
        actor=actor,
    )
    match.status = FoodMatchStatus.ACCEPTED
    match.reservation_id = reservation.id
    match.accepted_by_id = actor.id
    db.flush()
    audit(
        db,
        actor.id,
        "food_match.accepted",
        "food_match",
        match.id,
        request_id,
        {"reservation_id": str(reservation.id), "quantity": quantity},
    )
    return _match_out(match)


def decline_match(db: Session, match_id: UUID, actor: User, request_id: str) -> FoodMatchOut:
    match = _load_match_for_update(db, match_id)
    if match is None or match.food is None or not _can_access_match(actor, match, match.food):
        raise ApiError(404, "FOOD_MATCH_NOT_FOUND", "This recommendation was not found.")
    if match.status == FoodMatchStatus.DECLINED:
        return _match_out(match)
    if match.status != FoodMatchStatus.RECOMMENDED:
        raise ApiError(409, "INVALID_MATCH_TRANSITION", "This recommendation cannot be declined.")
    match.status = FoodMatchStatus.DECLINED
    match.declined_by_id = actor.id
    audit(db, actor.id, "food_match.declined", "food_match", match.id, request_id)
    return _match_out(match)


def list_owned_published_foods(db: Session, user: User) -> list[FoodListing]:
    return list(
        db.scalars(
            select(FoodListing).where(
                FoodListing.provider_id == user.id,
                FoodListing.status == FoodStatus.PUBLISHED,
            )
        )
    )
