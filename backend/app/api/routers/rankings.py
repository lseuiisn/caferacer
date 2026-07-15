from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models.drive import DriveRecord
from app.models.catalog import Course
from app.models.enums import (
    CrewMemberStatus,
    RankingMode,
    RecordStatus,
    RecordValidationStatus,
)
from app.models.social import (
    CrewCourse,
    CrewMember,
    LightningCourse,
    LightningCourseParticipant,
)
from app.models.user import User
from app.schemas.crews import RankingItem, RankingResponse

router = APIRouter(prefix="/rankings", tags=["rankings"])
SAFETY_NOTICE = "교통법규를 준수하고 기록 경쟁보다 안전 운전을 우선해 주세요."


def ranking_items(
    rows: list[tuple[DriveRecord, User]], baseline_seconds: int | None = None
) -> list[RankingItem]:
    return [
        RankingItem(
            rank=index,
            user_id=user.id,
            nickname=user.nickname,
            duration_seconds=record.duration_seconds or 0,
            baseline_delta_seconds=(
                (record.duration_seconds or 0) - baseline_seconds
                if baseline_seconds is not None
                else record.baseline_delta_seconds or 0
            ),
        )
        for index, (record, user) in enumerate(rows, start=1)
    ]


@router.get("/courses/{course_id}", response_model=RankingResponse)
def course_ranking(course_id: int, db: DbSession, limit: int = 100) -> RankingResponse:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    baseline_seconds = course.estimated_duration_minutes * 60
    rows = list(db.execute(
        select(DriveRecord, User)
        .join(User, User.id == DriveRecord.user_id)
        .where(
            DriveRecord.course_id == course_id,
            DriveRecord.status == RecordStatus.COMPLETED,
            DriveRecord.validation_status == RecordValidationStatus.VALID,
            DriveRecord.ranking_eligible.is_(True),
        )
        .order_by(DriveRecord.duration_seconds.asc(), DriveRecord.completed_at.asc())
        .limit(min(max(limit, 1), 100))
    ))
    return RankingResponse(
        mode=RankingMode.FASTEST,
        baseline_duration_seconds=baseline_seconds,
        safety_notice=SAFETY_NOTICE,
        items=ranking_items(rows, baseline_seconds),
    )


@router.get("/crew-courses/{crew_course_id}", response_model=RankingResponse)
def crew_course_ranking(
    crew_course_id: int, current_user: CurrentUser, db: DbSession, limit: int = 100
) -> RankingResponse:
    crew_course = db.get(CrewCourse, crew_course_id)
    if crew_course is None:
        raise HTTPException(status_code=404, detail="Crew course not found")
    member = db.scalar(select(CrewMember).where(
        CrewMember.crew_id == crew_course.crew_id,
        CrewMember.user_id == current_user.id,
        CrewMember.status == CrewMemberStatus.ACTIVE,
    ))
    if member is None:
        raise HTTPException(status_code=403, detail="Active crew membership required")
    query = (
        select(DriveRecord, User)
        .join(User, User.id == DriveRecord.user_id)
        .where(
            DriveRecord.crew_course_id == crew_course_id,
            DriveRecord.status == RecordStatus.COMPLETED,
            DriveRecord.validation_status == RecordValidationStatus.VALID,
            DriveRecord.ranking_eligible.is_(True),
        )
    )
    if crew_course.ranking_mode == RankingMode.FASTEST:
        query = query.order_by(DriveRecord.duration_seconds.asc())
    else:
        query = query.order_by(
            func.abs(DriveRecord.duration_seconds - crew_course.baseline_duration_seconds).asc(),
            DriveRecord.duration_seconds.asc(),
        )
    rows = list(db.execute(query.limit(min(max(limit, 1), 100))))
    return RankingResponse(
        mode=crew_course.ranking_mode,
        baseline_duration_seconds=crew_course.baseline_duration_seconds,
        safety_notice=SAFETY_NOTICE,
        items=ranking_items(rows, crew_course.baseline_duration_seconds),
    )


@router.get("/lightning-courses/{lightning_course_id}", response_model=RankingResponse)
def lightning_course_ranking(
    lightning_course_id: int,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = 100,
) -> RankingResponse:
    course = db.get(LightningCourse, lightning_course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Lightning course not found")
    participant = db.get(LightningCourseParticipant, {
        "lightning_course_id": lightning_course_id,
        "user_id": current_user.id,
    })
    if participant is None:
        raise HTTPException(status_code=403, detail="Join the lightning course first")
    query = (
        select(DriveRecord, User)
        .join(User, User.id == DriveRecord.user_id)
        .where(
            DriveRecord.lightning_course_id == lightning_course_id,
            DriveRecord.status == RecordStatus.COMPLETED,
            DriveRecord.validation_status == RecordValidationStatus.VALID,
            DriveRecord.ranking_eligible.is_(True),
        )
    )
    if course.ranking_mode == RankingMode.FASTEST:
        query = query.order_by(DriveRecord.duration_seconds.asc(), DriveRecord.completed_at.asc())
    else:
        query = query.order_by(
            func.abs(DriveRecord.duration_seconds - course.baseline_duration_seconds).asc(),
            DriveRecord.duration_seconds.asc(),
        )
    rows = list(db.execute(query.limit(min(max(limit, 1), 100))))
    return RankingResponse(
        mode=course.ranking_mode,
        baseline_duration_seconds=course.baseline_duration_seconds,
        safety_notice=SAFETY_NOTICE,
        items=ranking_items(rows, course.baseline_duration_seconds),
    )
