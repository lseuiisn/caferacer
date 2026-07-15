from datetime import UTC, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.catalog import Course
from app.models.drive import DriveRecord, DriveRecordAnchorPass, DriveRecordPoint
from app.models.enums import RecordStatus, RecordValidationStatus
from app.models.enums import CrewMemberStatus
from app.models.social import (
    CrewCourse,
    CrewMember,
    LightningCourse,
    LightningCourseParticipant,
)
from app.repositories.catalog import CatalogRepository
from app.repositories.drive_records import DriveRecordRepository
from app.schemas.drive_records import (
    DrivePointBatch,
    DrivePointBatchResponse,
    DriveRecordComplete,
    DriveRecordCreate,
    DriveRecordPage,
    DriveRecordResponse,
)
from app.services.drive_tracking import (
    distance_meters,
    is_ranking_eligible,
    matched_anchors,
    path_coverage,
    travelled_distance,
)

router = APIRouter(prefix="/drive-records", tags=["drive-records"])
me_router = APIRouter(prefix="/me", tags=["drive-records"])
SEOUL = timezone(timedelta(hours=9))
records = DriveRecordRepository()
catalog = CatalogRepository()


def naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def owned_record(record_id: int, user: CurrentUser, db: DbSession) -> DriveRecord:
    record = records.get_owned(db, record_id, user.id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive record not found")
    return record


@router.post("", response_model=DriveRecordResponse, status_code=status.HTTP_201_CREATED)
def create_drive_record(
    payload: DriveRecordCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> DriveRecord:
    if payload.course_id is not None:
        course = catalog.get_course(db, payload.course_id)
        if course is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        if not catalog.course_paths(db, payload.course_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Course path is not configured")
        if not catalog.course_navigation_anchors(db, payload.course_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Course navigation anchors are not configured",
            )
    elif payload.crew_course_id is not None:
        crew_course = db.get(CrewCourse, payload.crew_course_id)
        if crew_course is None or not crew_course.is_active:
            raise HTTPException(status_code=404, detail="Crew course not found")
        if crew_course.event_date and crew_course.event_date != datetime.now(SEOUL).date():
            raise HTTPException(status_code=409, detail="Crew lightning course is not active today")
        membership = db.scalar(
            select(CrewMember).where(
                CrewMember.crew_id == crew_course.crew_id,
                CrewMember.user_id == current_user.id,
                CrewMember.status == CrewMemberStatus.ACTIVE,
            )
        )
        if membership is None:
            raise HTTPException(status_code=403, detail="Active crew membership required")
    else:
        lightning_course = db.get(LightningCourse, payload.lightning_course_id)
        if lightning_course is None or not lightning_course.is_active:
            raise HTTPException(status_code=404, detail="Lightning course not found")
        if lightning_course.event_date != datetime.now(SEOUL).date():
            raise HTTPException(status_code=409, detail="Lightning course is not active today")
        participant = db.get(
            LightningCourseParticipant,
            {
                "lightning_course_id": lightning_course.id,
                "user_id": current_user.id,
            },
        )
        if participant is None:
            raise HTTPException(status_code=403, detail="Join the lightning course first")
    record = DriveRecord(
        user_id=current_user.id,
        course_id=payload.course_id,
        crew_course_id=payload.crew_course_id,
        lightning_course_id=payload.lightning_course_id,
        started_at=naive_utc(payload.started_at),
        status=RecordStatus.RECORDING,
        validation_status=RecordValidationStatus.PENDING,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/{record_id}/points", response_model=DrivePointBatchResponse)
def append_drive_points(
    record_id: int,
    payload: DrivePointBatch,
    current_user: CurrentUser,
    db: DbSession,
) -> DrivePointBatchResponse:
    record = owned_record(record_id, current_user, db)
    if record.status != RecordStatus.RECORDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Drive record is not recording")
    last_sequence = records.last_sequence(db, record.id)
    if last_sequence is not None and payload.points[0].sequence <= last_sequence:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Point sequence must be greater than {last_sequence}",
        )
    path = records.path(db, record.course_id) if record.course_id is not None else []
    for point in payload.points:
        nearest_distance = (
            min(
                distance_meters(
                    point.latitude,
                    point.longitude,
                    float(path_point.latitude),
                    float(path_point.longitude),
                )
                for path_point in path
            )
            if path
            else None
        )
        db.add(
            DriveRecordPoint(
                drive_record_id=record.id,
                sequence=point.sequence,
                recorded_at=naive_utc(point.recorded_at),
                latitude=point.latitude,
                longitude=point.longitude,
                accuracy_meters=point.accuracy_meters,
                speed_mps=point.speed_mps,
                heading_degrees=point.heading_degrees,
                distance_from_path_meters=(
                    round(nearest_distance, 2) if nearest_distance is not None else None
                ),
            )
        )
    db.commit()
    return DrivePointBatchResponse(
        accepted_count=len(payload.points),
        last_sequence=payload.points[-1].sequence,
    )


@router.post("/{record_id}/complete", response_model=DriveRecordResponse)
def complete_drive_record(
    record_id: int,
    payload: DriveRecordComplete,
    current_user: CurrentUser,
    db: DbSession,
) -> DriveRecord:
    record = owned_record(record_id, current_user, db)
    if record.status != RecordStatus.RECORDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Drive record is not recording")
    completed_at = naive_utc(payload.completed_at)
    if completed_at <= record.started_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Completion time must be after start time",
        )

    record.status = RecordStatus.VERIFYING
    points = records.points(db, record.id)
    if record.course_id is not None:
        path = records.path(db, record.course_id)
        anchors = records.anchors(db, record.course_id)
        matches = matched_anchors(points, anchors)
        coverage = path_coverage(points, path)
        eligible = is_ranking_eligible(coverage, len(matches), len(anchors))
        for match in matches:
            db.add(
                DriveRecordAnchorPass(
                    drive_record_id=record.id,
                    anchor_id=match.anchor.id,
                    passed_at=match.passed_at,
                    minimum_distance_meters=match.minimum_distance_meters,
                )
            )
        baseline_seconds = db.get(Course, record.course_id).estimated_duration_minutes * 60
    elif record.crew_course_id is not None:
        crew_course = db.get(CrewCourse, record.crew_course_id)
        usable = [
            point
            for point in points
            if point.accuracy_meters is None or float(point.accuracy_meters) <= 50
        ]
        start_passed = any(
            distance_meters(
                float(point.latitude),
                float(point.longitude),
                float(crew_course.start_latitude),
                float(crew_course.start_longitude),
            )
            <= 200
            for point in usable
        )
        destination_passed = any(
            distance_meters(
                float(point.latitude),
                float(point.longitude),
                float(crew_course.destination_latitude),
                float(crew_course.destination_longitude),
            )
            <= 200
            for point in usable
        )
        coverage = 100 if start_passed and destination_passed else 0
        eligible = start_passed and destination_passed and len(usable) >= 2
        baseline_seconds = crew_course.baseline_duration_seconds
    else:
        lightning_course = db.get(LightningCourse, record.lightning_course_id)
        usable = [
            point for point in points
            if point.accuracy_meters is None or float(point.accuracy_meters) <= 50
        ]
        start_passed = any(
            distance_meters(
                float(point.latitude), float(point.longitude),
                float(lightning_course.start_latitude), float(lightning_course.start_longitude),
            ) <= 200
            for point in usable
        )
        destination_passed = any(
            distance_meters(
                float(point.latitude), float(point.longitude),
                float(lightning_course.destination_latitude), float(lightning_course.destination_longitude),
            ) <= 200
            for point in usable
        )
        coverage = 100 if start_passed and destination_passed else 0
        eligible = start_passed and destination_passed and len(usable) >= 2
        baseline_seconds = lightning_course.baseline_duration_seconds

    duration_seconds = round((completed_at - record.started_at).total_seconds())
    record.completed_at = completed_at
    record.duration_seconds = duration_seconds
    record.distance_meters = travelled_distance(points)
    record.baseline_delta_seconds = (
        duration_seconds - baseline_seconds if baseline_seconds is not None else None
    )
    record.path_coverage_percent = coverage
    record.ranking_eligible = eligible
    record.validation_status = (
        RecordValidationStatus.VALID if eligible else RecordValidationStatus.INVALID
    )
    record.status = RecordStatus.COMPLETED
    db.commit()
    db.refresh(record)
    return record


@router.post("/{record_id}/cancel", response_model=DriveRecordResponse)
def cancel_drive_record(
    record_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> DriveRecord:
    record = owned_record(record_id, current_user, db)
    if record.status != RecordStatus.RECORDING:
        raise HTTPException(status_code=409, detail="Only a recording drive can be cancelled")
    record.status = RecordStatus.CANCELLED
    record.ranking_eligible = False
    db.commit()
    db.refresh(record)
    return record


@router.get("/{record_id}", response_model=DriveRecordResponse)
def get_drive_record(
    record_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> DriveRecord:
    return owned_record(record_id, current_user, db)


@router.get("", response_model=DriveRecordPage)
@me_router.get("/drive-records", response_model=DriveRecordPage)
def list_my_drive_records(
    current_user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> DriveRecordPage:
    items, total = records.list_owned(db, current_user.id, page=page, size=size)
    return DriveRecordPage(items=items, page=page, size=size, total=total)
