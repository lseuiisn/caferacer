from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.enums import ReportStatus, UserRole
from app.models.social import Report

router = APIRouter(prefix="/admin/reports", tags=["admin"])


class ReportStatusUpdate(BaseModel):
    status: ReportStatus


class ReportResponse(BaseModel):
    id: int
    reporter_id: int
    target_type: str
    target_id: int
    reason: str
    details: str | None
    status: ReportStatus


def require_admin(user: CurrentUser) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Administrator role required")


@router.get("", response_model=list[ReportResponse])
def list_reports(current_user: CurrentUser, db: DbSession) -> list[Report]:
    require_admin(current_user)
    return list(db.scalars(select(Report).order_by(Report.created_at.desc()).limit(200)))


@router.patch("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    payload: ReportStatusUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> Report:
    require_admin(current_user)
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = payload.status
    db.commit()
    db.refresh(report)
    return report
