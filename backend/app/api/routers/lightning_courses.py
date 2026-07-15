from datetime import UTC, date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models.social import LightningCourse, LightningCourseParticipant
from app.schemas.lightning_courses import (
    LightningCourseCreate,
    LightningCoursePage,
    LightningCourseResponse,
)
from app.schemas.recommendations import Coordinate

router = APIRouter(prefix="/lightning-courses", tags=["lightning-courses"])
SEOUL = timezone(timedelta(hours=9))


def now_utc_naive() -> datetime:
    return datetime.now(tz=UTC).replace(tzinfo=None)


def response(db: DbSession, course: LightningCourse, user_id: int) -> LightningCourseResponse:
    participant_count = db.scalar(
        select(func.count()).select_from(LightningCourseParticipant).where(
            LightningCourseParticipant.lightning_course_id == course.id
        )
    ) or 0
    joined = db.get(
        LightningCourseParticipant,
        {"lightning_course_id": course.id, "user_id": user_id},
    ) is not None
    return LightningCourseResponse(
        id=course.id,
        created_by_user_id=course.created_by_user_id,
        name=course.name,
        event_date=course.event_date,
        start_name=course.start_name,
        start=Coordinate(latitude=float(course.start_latitude), longitude=float(course.start_longitude)),
        destination_name=course.destination_name,
        destination=Coordinate(
            latitude=float(course.destination_latitude),
            longitude=float(course.destination_longitude),
        ),
        ranking_mode=course.ranking_mode,
        baseline_duration_seconds=course.baseline_duration_seconds,
        participant_count=participant_count,
        joined_by_me=joined,
        created_at=course.created_at,
    )


@router.get("", response_model=LightningCoursePage)
def list_lightning_courses(
    current_user: CurrentUser,
    db: DbSession,
    event_date: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> LightningCoursePage:
    target_date = event_date or datetime.now(SEOUL).date()
    filters = [
        LightningCourse.event_date == target_date,
        LightningCourse.is_active.is_(True),
    ]
    total = db.scalar(select(func.count()).select_from(LightningCourse).where(*filters)) or 0
    items = list(db.scalars(
        select(LightningCourse)
        .where(*filters)
        .order_by(LightningCourse.created_at.desc(), LightningCourse.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ))
    return LightningCoursePage(
        items=[response(db, item, current_user.id) for item in items],
        page=page,
        size=size,
        total=total,
    )


@router.get("/{course_id}", response_model=LightningCourseResponse)
def get_lightning_course(
    course_id: int, current_user: CurrentUser, db: DbSession
) -> LightningCourseResponse:
    course = db.get(LightningCourse, course_id)
    if course is None or not course.is_active:
        raise HTTPException(status_code=404, detail="Lightning course not found")
    return response(db, course, current_user.id)


@router.post("", response_model=LightningCourseResponse, status_code=status.HTTP_201_CREATED)
def create_lightning_course(
    payload: LightningCourseCreate, current_user: CurrentUser, db: DbSession
) -> LightningCourseResponse:
    if payload.event_date < datetime.now(SEOUL).date():
        raise HTTPException(status_code=422, detail="event_date cannot be in the past")
    course = LightningCourse(
        created_by_user_id=current_user.id,
        name=payload.name,
        event_date=payload.event_date,
        start_name=payload.start_name,
        start_latitude=payload.start.latitude,
        start_longitude=payload.start.longitude,
        destination_name=payload.destination_name,
        destination_latitude=payload.destination.latitude,
        destination_longitude=payload.destination.longitude,
        baseline_duration_seconds=payload.baseline_duration_seconds,
        ranking_mode=payload.ranking_mode,
    )
    db.add(course)
    db.flush()
    db.add(LightningCourseParticipant(
        lightning_course_id=course.id,
        user_id=current_user.id,
        joined_at=now_utc_naive(),
    ))
    db.commit()
    db.refresh(course)
    return response(db, course, current_user.id)


@router.post("/{course_id}/join", response_model=LightningCourseResponse)
def join_lightning_course(
    course_id: int, current_user: CurrentUser, db: DbSession
) -> LightningCourseResponse:
    course = db.get(LightningCourse, course_id)
    if course is None or not course.is_active:
        raise HTTPException(status_code=404, detail="Lightning course not found")
    if course.event_date != datetime.now(SEOUL).date():
        raise HTTPException(status_code=409, detail="Only today's lightning course can be joined")
    key = {"lightning_course_id": course_id, "user_id": current_user.id}
    if db.get(LightningCourseParticipant, key) is None:
        db.add(LightningCourseParticipant(**key, joined_at=now_utc_naive()))
        db.commit()
    return response(db, course, current_user.id)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lightning_course(course_id: int, current_user: CurrentUser, db: DbSession) -> None:
    course = db.get(LightningCourse, course_id)
    if course is None or course.created_by_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Lightning course not found")
    course.is_active = False
    db.commit()
