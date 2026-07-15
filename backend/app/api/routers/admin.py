from datetime import UTC, datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.catalog import Cafe, CafeDataSource, CafeImportCandidate
from app.models.enums import UserRole
from app.schemas.admin import CafeImportRequest, CafeImportResponse, CafeImportReview

router = APIRouter(prefix="/admin/cafe-imports", tags=["admin"])


def require_admin(user: CurrentUser) -> None:
    if user.role is not UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")


@router.post("", response_model=CafeImportResponse, summary="카페 검수 후보 생성")
def create_candidate(payload: CafeImportRequest, user: CurrentUser, db: DbSession) -> CafeImportResponse:
    require_admin(user)
    candidate = CafeImportCandidate(name=payload.name, address=payload.address, source_url=payload.source_url, search_url=f"https://map.naver.com/p/search/{quote(payload.name)}", submitted_by_user_id=user.id)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return CafeImportResponse(id=candidate.id, name=candidate.name, address=candidate.address, search_url=candidate.search_url, status=candidate.status)


@router.get("", response_model=list[CafeImportResponse], summary="검수 대기 카페 후보 조회")
def list_candidates(user: CurrentUser, db: DbSession) -> list[CafeImportResponse]:
    require_admin(user)
    candidates = db.scalars(select(CafeImportCandidate).where(CafeImportCandidate.status == "pending_review").order_by(CafeImportCandidate.created_at)).all()
    return [CafeImportResponse(id=item.id, name=item.name, address=item.address, search_url=item.search_url, status=item.status) for item in candidates]


@router.patch("/{candidate_id}/approve", response_model=CafeImportResponse, summary="검수 후보 승인 후 카페 등록")
def approve_candidate(candidate_id: int, payload: CafeImportReview, user: CurrentUser, db: DbSession) -> CafeImportResponse:
    require_admin(user)
    candidate = db.get(CafeImportCandidate, candidate_id)
    if candidate is None or candidate.status != "pending_review":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending candidate not found")
    cafe = Cafe(name=candidate.name, address=payload.address, latitude=payload.coordinate.latitude, longitude=payload.coordinate.longitude, price_range=payload.price_range, parking_available=payload.parking_available, verified_at=datetime.now(UTC).replace(tzinfo=None))
    db.add(cafe)
    db.flush()
    db.add(CafeDataSource(cafe_id=cafe.id, source_type="operator_verified", source_url=payload.source_url, collected_at=datetime.now(UTC).replace(tzinfo=None), verified_at=datetime.now(UTC).replace(tzinfo=None)))
    candidate.status = "approved"
    candidate.reviewed_by_user_id = user.id
    candidate.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return CafeImportResponse(id=candidate.id, name=candidate.name, address=payload.address, search_url=candidate.search_url, status=candidate.status, cafe_id=cafe.id)
