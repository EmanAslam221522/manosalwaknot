from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.domain import audit
from app.models import Report, Role, User, VerificationRequest, VerificationStatus
from app.schemas import AdminReportUpdate, AdminVerificationUpdate, ReportOut, VerificationOut

router = APIRouter(prefix="/admin", tags=["administration"])


@router.put("/verification-requests/{request_id}", response_model=VerificationOut)
def review_verification(request_id: UUID, payload: AdminVerificationUpdate, request: Request, admin: User = Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)), db: Session = Depends(get_db)) -> VerificationOut:
    record = db.scalar(select(VerificationRequest).where(VerificationRequest.id == request_id).with_for_update())
    if record is None:
        raise ApiError(404, "VERIFICATION_NOT_FOUND", "This verification request was not found.")
    record.status, record.reviewer_message, record.reviewed_by_id = payload.status, payload.reviewer_message, admin.id
    if payload.status == VerificationStatus.APPROVED:
        target = db.get(User, record.user_id)
        if target:
            target.is_verified = True
    audit(db, admin.id, "verification.reviewed", "verification_request", record.id, request.state.request_id, {"status": payload.status.value})
    db.commit()
    return VerificationOut(id=record.id, type=record.type, status=record.status, submitted_at=record.submitted_at, reviewer_message=record.reviewer_message)


@router.put("/reports/{report_id}", response_model=ReportOut)
def review_report(report_id: UUID, payload: AdminReportUpdate, request: Request, admin: User = Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)), db: Session = Depends(get_db)) -> ReportOut:
    report = db.scalar(select(Report).where(Report.id == report_id).with_for_update())
    if report is None:
        raise ApiError(404, "REPORT_NOT_FOUND", "This report was not found.")
    report.status, report.resolved_by_id = payload.status, admin.id
    audit(db, admin.id, "report.reviewed", "report", report.id, request.state.request_id, {"status": payload.status.value})
    db.commit()
    return ReportOut(id=report.id, reason=report.reason, status=report.status, created_at=report.created_at, updated_at=report.updated_at)
