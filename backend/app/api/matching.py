from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_roles
from app.core.database import get_db
from app.matching.schemas import (
    FoodMatchOut,
    FoodMatchPage,
    MatchAcceptIn,
    OrganizationProfileIn,
    OrganizationProfileOut,
)
from app.matching.service import (
    accept_match,
    decline_match,
    generate_recommendations,
    get_own_profile,
    list_recommendations,
    profile_out,
    upsert_organization_profile,
)
from app.models import Role, User

router = APIRouter(prefix="/matching", tags=["matching"])


@router.get("/organization-profile/me", response_model=OrganizationProfileOut)
def read_organization_profile(
    user: User = Depends(require_roles(Role.ORGANIZATION)),
    db: Session = Depends(get_db),
) -> OrganizationProfileOut:
    return profile_out(get_own_profile(db, user))


@router.put("/organization-profile", response_model=OrganizationProfileOut)
def save_organization_profile(
    payload: OrganizationProfileIn,
    request: Request,
    user: User = Depends(require_roles(Role.ORGANIZATION)),
    db: Session = Depends(get_db),
) -> OrganizationProfileOut:
    profile = upsert_organization_profile(db, user, payload, request.state.request_id)
    db.commit()
    return profile_out(profile)


@router.post(
    "/food/{food_id}/recommendations",
    response_model=FoodMatchPage,
    status_code=status.HTTP_200_OK,
)
def create_recommendations(
    food_id: UUID,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FoodMatchPage:
    page = generate_recommendations(db, food_id, user, request.state.request_id)
    db.commit()
    return page


@router.get("/food/{food_id}/recommendations", response_model=FoodMatchPage)
def read_recommendations(
    food_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FoodMatchPage:
    return list_recommendations(db, food_id, user)


@router.post("/matches/{match_id}/accept", response_model=FoodMatchOut)
def post_accept_match(
    match_id: UUID,
    payload: MatchAcceptIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FoodMatchOut:
    result = accept_match(db, match_id, user, payload.quantity, request.state.request_id)
    db.commit()
    return result


@router.post("/matches/{match_id}/decline", response_model=FoodMatchOut)
def post_decline_match(
    match_id: UUID,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FoodMatchOut:
    result = decline_match(db, match_id, user, request.state.request_id)
    db.commit()
    return result
