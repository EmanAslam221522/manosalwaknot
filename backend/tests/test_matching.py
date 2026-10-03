"""Unit tests for Feature 1 – Smart Recipient Matching.

Covers:
- verified / unverified / inactive organization eligibility
- insufficient capacity
- expired food
- incompatible pickup window
- no matches
- concurrent allocation
- inventory changed after recommendation
- accepted / declined match
- overnight pickup window
- out-of-range distance
- incompatible category
- missing profile / missing role
- scoring determinism
- explanation formatting
"""
from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.errors import ApiError
from app.matching.eligibility import (
    EXPIRED_FOOD,
    INACTIVE,
    INCOMPATIBLE_CATEGORY,
    INCOMPATIBLE_PICKUP_WINDOW,
    INSUFFICIENT_CAPACITY,
    MISSING_PROFILE,
    NOT_ORGANIZATION,
    NOT_PUBLISHED,
    OUT_OF_RANGE,
    OWN_LISTING,
    UNVERIFIED,
    EligibilityResult,
    FoodFacts,
    OrganizationFacts,
    evaluate_eligibility,
    pickup_window_overlap_minutes,
)
from app.matching.schemas import (
    MatchingWeights,
    ScoreBreakdownOut,
)
from app.matching.scoring import (
    ScoreInputs,
    capacity_score,
    configured_weights,
    demand_score,
    explanation_from_evidence,
    location_score,
    readiness_score,
    score_match,
    timing_score,
)
from app.models import (
    FoodListing,
    FoodMatch,
    FoodMatchStatus,
    FoodStatus,
    Location,
    OrganizationProfile,
    OrganizationType,
    Role,
    User,
    UserRole,
)


# ── helpers ──────────────────────────────────────────────────────────────────


def _base_food(
    *,
    food_id=None,
    provider_id=None,
    status=FoodStatus.PUBLISHED,
    servings_available=50,
    expires_at=None,
    pickup_start=None,
    pickup_end=None,
    category_id=None,
    latitude=33.9946,
    longitude=72.9106,
) -> FoodFacts:
    now = datetime.now(UTC)
    return FoodFacts(
        id=food_id or uuid4(),
        provider_id=provider_id or uuid4(),
        status=status,
        servings_available=servings_available,
        expires_at=expires_at or (now + timedelta(hours=6)),
        pickup_start=pickup_start or (now + timedelta(hours=1)),
        pickup_end=pickup_end or (now + timedelta(hours=5)),
        category_id=category_id or uuid4(),
        latitude=latitude,
        longitude=longitude,
    )


def _base_org(
    *,
    user_id=None,
    display_name="Helping Hands NGO",
    is_active_user=True,
    deleted=False,
    is_verified=True,
    has_organization_role=True,
    verification_approved=True,
    profile_present=True,
    profile_active=True,
    daily_capacity=100,
    remaining_capacity=100,
    accepted_category_ids=None,
    pickup_window_start=time(0, 0),
    pickup_window_end=time(23, 59),
    max_distance_km=15.0,
    people_served=200,
    latitude=34.0040,
    longitude=72.9200,
) -> OrganizationFacts:
    return OrganizationFacts(
        user_id=user_id or uuid4(),
        display_name=display_name,
        is_active_user=is_active_user,
        deleted=deleted,
        is_verified=is_verified,
        has_organization_role=has_organization_role,
        verification_approved=verification_approved,
        profile_present=profile_present,
        profile_active=profile_active,
        daily_capacity=daily_capacity,
        remaining_capacity=remaining_capacity,
        accepted_category_ids=accepted_category_ids or frozenset(),
        pickup_window_start=pickup_window_start,
        pickup_window_end=pickup_window_end,
        max_distance_km=max_distance_km,
        people_served=people_served,
        latitude=latitude,
        longitude=longitude,
    )


def _mock_user(
    user_id=None, display_name="Org User", roles=None
) -> User:
    u = User(
        email=f"org-{uuid4()}@example.com",
        display_name=display_name,
        is_verified=True,
        is_active=True,
    )
    u.id = user_id or uuid4()
    u.roles = [
        UserRole(user_id=u.id, role=r)
        for r in (roles or [Role.ORGANIZATION])
    ]
    return u


def _make_location(owner_id, **overrides):
    """Build a Location without the non-existent *label* column."""
    defaults = dict(
        owner_id=owner_id,
        address="123 Hospital Road, Haripur",
        city="Haripur",
        area="City Center",
        latitude=Decimal("33.9946"),
        longitude=Decimal("72.9106"),
    )
    defaults.update(overrides)
    loc = Location(**defaults)
    loc.id = uuid4()
    return loc


def _mock_food_entity(
    food_id=None,
    provider=None,
    status=FoodStatus.PUBLISHED,
    servings=50,
) -> FoodListing:
    now = datetime.now(UTC)
    prov = provider or _mock_user(
        display_name="Provider User", roles=[Role.FOOD_PROVIDER]
    )
    loc = _make_location(prov.id)
    f = FoodListing(
        provider_id=prov.id,
        category_id=uuid4(),
        location_id=loc.id,
        title="Biryani Servings",
        description="Fresh hot biryani",
        quantity=50,
        servings_total=50,
        servings_available=servings,
        unit="servings",
        price=Decimal("0.00"),
        currency="PKR",
        is_free=True,
        pickup_start=now + timedelta(hours=1),
        pickup_end=now + timedelta(hours=4),
        expires_at=now + timedelta(hours=6),
        city=loc.city,
        area=loc.area,
        latitude=loc.latitude,
        longitude=loc.longitude,
        ingredients=["rice", "chicken"],
        allergens=[],
        dietary_information={},
        preparation_time=now,
        provider_safety_confirmed=True,
        delivery_available=False,
        status=status,
    )
    f.id = food_id or uuid4()
    f.provider = prov
    f.location = loc
    return f


def _mock_org_profile(user: User, loc: Location) -> OrganizationProfile:
    prof = OrganizationProfile(
        user_id=user.id,
        location_id=loc.id,
        organization_type=OrganizationType.NGO,
        daily_capacity=100,
        people_served=250,
        accepted_category_ids=[],
        pickup_window_start=time(0, 0),
        pickup_window_end=time(23, 59),
        max_distance_km=Decimal("20.00"),
        is_active=True,
    )
    prof.id = uuid4()
    prof.user = user
    prof.location = loc
    return prof


def _make_match(
    food: FoodListing,
    org_user: User,
    org_prof: OrganizationProfile,
    *,
    status=FoodMatchStatus.RECOMMENDED,
    score="97.00",
    quantity_snapshot=None,
) -> FoodMatch:
    breakdown = ScoreBreakdownOut(
        location=90.0,
        capacity=100.0,
        timing=100.0,
        demand=100.0,
        readiness=100.0,
        total=float(score),
        weights=configured_weights(),
    )
    m = FoodMatch(
        food_listing_id=food.id,
        organization_id=org_user.id,
        organization_profile_id=org_prof.id,
        status=status,
        quantity_snapshot=quantity_snapshot or food.servings_available,
        score=Decimal(score),
        score_breakdown=breakdown.model_dump(mode="json"),
        evidence={
            "distance_km": 0.5,
            "remaining_capacity": 100,
            "daily_capacity": 100,
            "overlap_minutes": 180,
            "people_served": 250,
            "organization_verified": True,
            "servings_available": food.servings_available,
            "organization_type": "NGO",
        },
        explanation=f"{org_user.display_name} is verified...",
    )
    m.id = uuid4()
    m.food = food
    m.organization = org_user
    m.profile = org_prof
    return m


# =========================================================================
# 1. ELIGIBILITY ENGINE
# =========================================================================


class TestEligibility:
    def test_verified_organization_is_eligible(self) -> None:
        now = datetime.now(UTC)
        res = evaluate_eligibility(_base_food(), _base_org(), now)
        assert res.eligible is True
        assert len(res.reasons) == 0
        assert res.distance_km is not None
        assert res.overlap_minutes > 0

    def test_unverified_user_flag(self) -> None:
        now = datetime.now(UTC)
        res = evaluate_eligibility(
            _base_food(),
            _base_org(is_verified=False),
            now,
        )
        assert res.eligible is False
        assert UNVERIFIED in res.reasons

    def test_unverified_verification_not_approved(self) -> None:
        now = datetime.now(UTC)
        res = evaluate_eligibility(
            _base_food(),
            _base_org(verification_approved=False),
            now,
        )
        assert res.eligible is False
        assert UNVERIFIED in res.reasons

    def test_inactive_user(self) -> None:
        now = datetime.now(UTC)
        res = evaluate_eligibility(
            _base_food(),
            _base_org(is_active_user=False),
            now,
        )
        assert res.eligible is False
        assert INACTIVE in res.reasons

    def test_deleted_user(self) -> None:
        now = datetime.now(UTC)
        res = evaluate_eligibility(
            _base_food(),
            _base_org(deleted=True),
            now,
        )
        assert res.eligible is False
        assert INACTIVE in res.reasons

    def test_inactive_profile(self) -> None:
        now = datetime.now(UTC)
        res = evaluate_eligibility(
            _base_food(),
            _base_org(profile_active=False),
            now,
        )
        assert res.eligible is False
        assert INACTIVE in res.reasons

    def test_insufficient_capacity(self) -> None:
        now = datetime.now(UTC)
        res = evaluate_eligibility(
            _base_food(),
            _base_org(remaining_capacity=0),
            now,
        )
        assert res.eligible is False
        assert INSUFFICIENT_CAPACITY in res.reasons

    def test_expired_food(self) -> None:
        now = datetime.now(UTC)
        res = evaluate_eligibility(
            _base_food(
                expires_at=now - timedelta(minutes=5),
                pickup_end=now - timedelta(minutes=10),
            ),
            _base_org(),
            now,
        )
        assert res.eligible is False
        assert EXPIRED_FOOD in res.reasons

    def test_incompatible_pickup_window(self) -> None:
        now = datetime.now(UTC)
        food_start = now.replace(hour=14, minute=0, second=0, microsecond=0)
        food_end = now.replace(hour=16, minute=0, second=0, microsecond=0)
        res = evaluate_eligibility(
            _base_food(pickup_start=food_start, pickup_end=food_end),
            _base_org(
                pickup_window_start=time(8, 0),
                pickup_window_end=time(11, 0),
            ),
            now,
        )
        assert res.eligible is False
        assert INCOMPATIBLE_PICKUP_WINDOW in res.reasons

    def test_overnight_pickup_window_overlap(self) -> None:
        base = datetime(2026, 10, 3, 2, 0, tzinfo=UTC)
        overlap = pickup_window_overlap_minutes(
            base,
            base + timedelta(hours=2),
            time(22, 0),
            time(6, 0),
        )
        assert overlap == 120

    def test_food_not_published_and_no_servings(self) -> None:
        now = datetime.now(UTC)
        res = evaluate_eligibility(
            _base_food(status=FoodStatus.DRAFT, servings_available=0),
            _base_org(),
            now,
        )
        assert res.eligible is False
        assert NOT_PUBLISHED in res.reasons
        assert "no_servings_available" in res.reasons

    def test_own_listing(self) -> None:
        now = datetime.now(UTC)
        shared = uuid4()
        res = evaluate_eligibility(
            _base_food(provider_id=shared),
            _base_org(user_id=shared),
            now,
        )
        assert res.eligible is False
        assert OWN_LISTING in res.reasons

    def test_out_of_range_distance(self) -> None:
        now = datetime.now(UTC)
        res = evaluate_eligibility(
            _base_food(latitude=33.9946, longitude=72.9106),
            _base_org(
                latitude=33.6844,
                longitude=73.0479,
                max_distance_km=10.0,
            ),
            now,
        )
        assert res.eligible is False
        assert OUT_OF_RANGE in res.reasons

    def test_incompatible_category(self) -> None:
        now = datetime.now(UTC)
        cat_a, cat_b = uuid4(), uuid4()
        res = evaluate_eligibility(
            _base_food(category_id=cat_a),
            _base_org(accepted_category_ids=frozenset([cat_b])),
            now,
        )
        assert res.eligible is False
        assert INCOMPATIBLE_CATEGORY in res.reasons

    def test_missing_profile_and_role(self) -> None:
        now = datetime.now(UTC)
        res = evaluate_eligibility(
            _base_food(),
            _base_org(
                profile_present=False,
                has_organization_role=False,
            ),
            now,
        )
        assert res.eligible is False
        assert MISSING_PROFILE in res.reasons
        assert NOT_ORGANIZATION in res.reasons


# =========================================================================
# 2. SCORING ENGINE
# =========================================================================


class TestScoring:
    def test_configured_weights_sum_to_one(self) -> None:
        w = configured_weights()
        total = w.location + w.capacity + w.timing + w.demand + w.readiness
        assert abs(total - 1.0) < 1e-6

    def test_location_score(self) -> None:
        assert location_score(0.0, 10.0) == 100.0
        assert location_score(5.0, 10.0) == 50.0
        assert location_score(12.0, 10.0) == 0.0

    def test_capacity_score(self) -> None:
        assert capacity_score(50, 50) == 100.0
        assert capacity_score(100, 50) == 100.0
        assert capacity_score(25, 50) == 50.0

    def test_timing_score(self) -> None:
        assert timing_score(120, 120) == 100.0
        assert timing_score(60, 120) == 50.0

    def test_demand_score(self) -> None:
        assert demand_score(200, 50) == 100.0
        assert demand_score(100, 50) == 50.0

    def test_readiness_score(self) -> None:
        assert readiness_score(True, True) == 100.0
        assert readiness_score(True, False) == 50.0
        assert readiness_score(False, True) == 0.0

    def test_deterministic_total(self) -> None:
        inputs = ScoreInputs(
            distance_km=2.0,
            max_distance_km=10.0,
            remaining_capacity=50,
            servings_available=50,
            overlap_minutes=120,
            food_window_minutes=120,
            people_served=200,
            verified=True,
            profile_complete=True,
        )
        weights = MatchingWeights(
            location=0.30,
            capacity=0.25,
            timing=0.20,
            demand=0.15,
            readiness=0.10,
        )
        res = score_match(inputs, weights)
        # 80*0.3 + 100*0.25 + 100*0.2 + 100*0.15 + 100*0.1 = 94.0
        assert res.total == 94.0

    def test_explanation_formatting(self) -> None:
        text = explanation_from_evidence(
            "Haripur Relief Foundation",
            "COMMUNITY_KITCHEN",
            1.5,
            80,
            120,
            300,
        )
        assert "Haripur Relief Foundation" in text
        assert "Community Kitchen" in text
        assert "1.5 km" in text
        assert "80 servings" in text


# =========================================================================
# 3. SERVICE LAYER  (mocked DB)
# =========================================================================


class TestServiceRecommendations:
    """Tests that exercise generate_recommendations through mocked DB."""

    def test_no_matches_returns_empty_page(self) -> None:
        from app.matching.service import generate_recommendations

        db = MagicMock()
        provider = _mock_user(
            display_name="Chef Ali", roles=[Role.FOOD_PROVIDER]
        )
        food = _mock_food_entity(provider=provider, servings=50)

        db.scalar.return_value = food
        db.scalars.return_value = MagicMock(all=lambda: [])

        page = generate_recommendations(db, food.id, provider, "req-1")
        assert page.food_listing_id == food.id
        assert len(page.items) == 0

    def test_unauthorized_actor_gets_404(self) -> None:
        from app.matching.service import generate_recommendations

        db = MagicMock()
        provider = _mock_user(
            display_name="Chef Ali", roles=[Role.FOOD_PROVIDER]
        )
        intruder = _mock_user(
            display_name="Stranger", roles=[Role.RECIPIENT]
        )
        food = _mock_food_entity(provider=provider)
        db.scalar.return_value = food

        with pytest.raises(ApiError) as exc:
            generate_recommendations(db, food.id, intruder, "req-2")
        assert exc.value.status_code == 404
        assert exc.value.code == "FOOD_NOT_FOUND"

    def test_expired_food_raises_409(self) -> None:
        from app.matching.service import generate_recommendations

        db = MagicMock()
        provider = _mock_user(roles=[Role.FOOD_PROVIDER])
        food = _mock_food_entity(provider=provider)
        food.expires_at = datetime.now(UTC) - timedelta(minutes=10)

        db.scalar.return_value = food
        db.scalars.return_value = []

        with pytest.raises(ApiError) as exc:
            generate_recommendations(db, food.id, provider, "req-3")
        assert exc.value.status_code == 409
        assert exc.value.code == "FOOD_EXPIRED"

    def test_with_eligible_org(self) -> None:
        from app.matching.service import generate_recommendations

        db = MagicMock()
        provider = _mock_user(roles=[Role.FOOD_PROVIDER])
        food = _mock_food_entity(provider=provider, servings=30)

        org_user = _mock_user(
            display_name="Hope Kitchen", roles=[Role.ORGANIZATION]
        )
        org_loc = _make_location(
            org_user.id,
            address="45 Nishtar Road",
            city="Haripur",
            area="Model Town",
            latitude=Decimal("33.9980"),
            longitude=Decimal("72.9150"),
        )
        org_prof = _mock_org_profile(org_user, org_loc)

        def scalar_router(query):
            q = str(query)
            if "food_listings" in q:
                return food
            if "reservations" in q:
                return 0
            if "food_matches" in q:
                return None
            return None

        db.scalar.side_effect = scalar_router

        def scalars_router(query):
            q = str(query)
            if "verification_requests" in q:
                return [org_user.id]
            if "organization_profiles" in q:
                return MagicMock(all=lambda: [org_prof])
            return []

        db.scalars.side_effect = scalars_router

        page = generate_recommendations(db, food.id, provider, "req-4")
        assert len(page.items) == 1
        out = page.items[0]
        assert out.organization_name == "Hope Kitchen"
        assert out.score > 0
        assert out.evidence.organization_verified is True
        assert out.status == FoodMatchStatus.RECOMMENDED


class TestServiceAcceptDecline:
    """Tests for accept / decline / concurrent allocation."""

    def _org_fixture(self, display_name="Care NGO"):
        org_user = _mock_user(
            display_name=display_name, roles=[Role.ORGANIZATION]
        )
        org_loc = _make_location(
            org_user.id,
            address="Station Road",
            city="Haripur",
            area="Downtown",
            latitude=Decimal("33.9950"),
            longitude=Decimal("72.9120"),
        )
        org_prof = _mock_org_profile(org_user, org_loc)
        return org_user, org_loc, org_prof

    def _accept_db(self, match, food):
        db = MagicMock()
        db.get.return_value = match

        def scalar_router(query):
            q = str(query)
            if "food_matches" in q:
                return match
            if "food_listings" in q:
                return food
            if "verification_requests" in q:
                return uuid4()
            if "reservations" in q:
                return 0
            return None

        db.scalar.side_effect = scalar_router
        return db

    def test_accept_creates_reservation(self) -> None:
        from app.matching.service import accept_match

        provider = _mock_user(roles=[Role.FOOD_PROVIDER])
        food = _mock_food_entity(provider=provider, servings=50)
        org_user, _, org_prof = self._org_fixture()
        match = _make_match(food, org_user, org_prof)
        db = self._accept_db(match, food)

        out = accept_match(db, match.id, provider, 20, "req-accept")
        assert out.status == FoodMatchStatus.ACCEPTED
        assert out.reservation_id is not None
        assert food.servings_available == 30

    def test_accept_is_idempotent(self) -> None:
        from app.matching.service import accept_match

        provider = _mock_user(roles=[Role.FOOD_PROVIDER])
        food = _mock_food_entity(provider=provider, servings=50)
        org_user, _, org_prof = self._org_fixture()
        match = _make_match(food, org_user, org_prof)
        db = self._accept_db(match, food)

        out1 = accept_match(db, match.id, provider, 20, "req-a1")
        out2 = accept_match(db, match.id, provider, 20, "req-a2")
        assert out1.reservation_id == out2.reservation_id

    def test_accept_fails_when_inventory_changed(self) -> None:
        from app.matching.service import accept_match

        provider = _mock_user(roles=[Role.FOOD_PROVIDER])
        food = _mock_food_entity(provider=provider, servings=5)
        org_user, _, org_prof = self._org_fixture()
        match = _make_match(
            food, org_user, org_prof, quantity_snapshot=50
        )
        db = self._accept_db(match, food)

        with pytest.raises(ApiError) as exc:
            accept_match(db, match.id, provider, 20, "req-inv")
        assert exc.value.status_code == 409
        assert exc.value.code == "RESERVATION_QUANTITY_UNAVAILABLE"

    def test_decline_match(self) -> None:
        from app.matching.service import decline_match

        provider = _mock_user(roles=[Role.FOOD_PROVIDER])
        food = _mock_food_entity(provider=provider, servings=50)
        org_user, _, org_prof = self._org_fixture()
        match = _make_match(food, org_user, org_prof)

        db = MagicMock()
        db.get.return_value = match
        db.scalar.return_value = match

        out = decline_match(db, match.id, provider, "req-dec")
        assert out.status == FoodMatchStatus.DECLINED

    def test_decline_is_idempotent(self) -> None:
        from app.matching.service import decline_match

        provider = _mock_user(roles=[Role.FOOD_PROVIDER])
        food = _mock_food_entity(provider=provider, servings=50)
        org_user, _, org_prof = self._org_fixture()
        match = _make_match(food, org_user, org_prof)

        db = MagicMock()
        db.get.return_value = match
        db.scalar.return_value = match

        out1 = decline_match(db, match.id, provider, "dec-1")
        out2 = decline_match(db, match.id, provider, "dec-2")
        assert out1.status == FoodMatchStatus.DECLINED
        assert out2.status == FoodMatchStatus.DECLINED

    def test_concurrent_allocation_second_fails(self) -> None:
        from app.matching.service import accept_match

        provider = _mock_user(roles=[Role.FOOD_PROVIDER])
        food = _mock_food_entity(provider=provider, servings=10)

        u1, _, p1 = self._org_fixture("Care NGO 1")
        u2, _, p2 = self._org_fixture("Care NGO 2")

        m1 = _make_match(food, u1, p1, quantity_snapshot=10)
        m2 = _make_match(food, u2, p2, score="95.00", quantity_snapshot=10)

        def mock_get(_model, pk):
            if pk == m1.id:
                return m1
            if pk == m2.id:
                return m2
            return None

        db = MagicMock()
        db.get.side_effect = mock_get

        def scalar_router(query):
            q = str(query)
            if "food_listings" in q:
                return food
            if "verification_requests" in q:
                return uuid4()
            if "reservations" in q:
                return 0
            if "food_matches" in q:
                return m1 if m1.status == FoodMatchStatus.RECOMMENDED else m2
            return None

        db.scalar.side_effect = scalar_router

        # First allocation drains all 10 servings
        r1 = accept_match(db, m1.id, provider, 10, "t1")
        assert r1.status == FoodMatchStatus.ACCEPTED
        assert food.servings_available == 0

        # Second should fail -- inventory exhausted
        with pytest.raises(ApiError) as exc:
            accept_match(db, m2.id, provider, 10, "t2")
        assert exc.value.status_code == 409
        assert exc.value.code in {
            "MATCH_NO_LONGER_ELIGIBLE",
            "RESERVATION_QUANTITY_UNAVAILABLE",
        }
