import hashlib
import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession
from app.models.enums import (
    CrewJoinPolicy,
    CrewMemberRole,
    CrewMemberStatus,
    CrewVisibility,
    RankingMode,
    RecordStatus,
    RecordValidationStatus,
)
from app.models.catalog import Course
from app.models.drive import DriveRecord
from app.models.social import (
    Crew,
    CrewCourse,
    CrewDailyCourseRanking,
    CrewInvitation,
    CrewMember,
    CrewMessage,
)
from app.models.user import User
from app.schemas.crews import (
    CrewCourseCreate,
    CrewCourseResponse,
    CrewCreate,
    CrewMessageCreate,
    CrewMessageResponse,
    CrewMemberResponse,
    CrewPage,
    CrewResponse,
    InvitationAccept,
    InvitationResponse,
)
from app.schemas.lightning_courses import (
    CrewDailyRankingResponse,
    CrewDailyRankingUpsert,
)
from app.schemas.crews import RankingItem, RankingResponse
from app.schemas.recommendations import Coordinate

router = APIRouter(prefix="/crews", tags=["crews"])


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def membership(db: DbSession, crew_id: int, user_id: int) -> CrewMember | None:
    return db.scalar(
        select(CrewMember).where(
            CrewMember.crew_id == crew_id,
            CrewMember.user_id == user_id,
        )
    )


def require_active_member(db: DbSession, crew_id: int, user_id: int) -> CrewMember:
    member = membership(db, crew_id, user_id)
    if member is None or member.status != CrewMemberStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Active crew membership required")
    return member


def require_manager(db: DbSession, crew_id: int, user_id: int) -> CrewMember:
    member = require_active_member(db, crew_id, user_id)
    if member.role not in {CrewMemberRole.OWNER, CrewMemberRole.MANAGER}:
        raise HTTPException(status_code=403, detail="Crew manager role required")
    return member


def crew_response(db: DbSession, crew: Crew, user_id: int) -> CrewResponse:
    member = membership(db, crew.id, user_id)
    count = db.scalar(
        select(func.count()).select_from(CrewMember).where(
            CrewMember.crew_id == crew.id,
            CrewMember.status == CrewMemberStatus.ACTIVE,
        )
    ) or 0
    return CrewResponse(
        id=crew.id,
        owner_id=crew.owner_id,
        name=crew.name,
        description=crew.description,
        image_url=crew.image_url,
        visibility=crew.visibility,
        join_policy=crew.join_policy,
        member_count=count,
        my_status=member.status if member else None,
    )


@router.get("", response_model=CrewPage)
def list_crews(
    current_user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> CrewPage:
    member_crew_ids = select(CrewMember.crew_id).where(CrewMember.user_id == current_user.id)
    filters = [
        Crew.is_active.is_(True),
        or_(Crew.visibility == CrewVisibility.PUBLIC, Crew.id.in_(member_crew_ids)),
    ]
    total = db.scalar(select(func.count()).select_from(Crew).where(*filters)) or 0
    crews = list(
        db.scalars(
            select(Crew)
            .where(*filters)
            .order_by(Crew.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    return CrewPage(
        items=[crew_response(db, crew, current_user.id) for crew in crews],
        page=page,
        size=size,
        total=total,
    )


@router.post("", response_model=CrewResponse, status_code=status.HTTP_201_CREATED)
def create_crew(payload: CrewCreate, current_user: CurrentUser, db: DbSession) -> CrewResponse:
    if db.scalar(select(Crew.id).where(Crew.name == payload.name)):
        raise HTTPException(status_code=409, detail="Crew name already exists")
    crew = Crew(owner_id=current_user.id, **payload.model_dump())
    db.add(crew)
    db.flush()
    db.add(
        CrewMember(
            crew_id=crew.id,
            user_id=current_user.id,
            role=CrewMemberRole.OWNER,
            status=CrewMemberStatus.ACTIVE,
            joined_at=utcnow(),
        )
    )
    db.commit()
    db.refresh(crew)
    return crew_response(db, crew, current_user.id)


@router.post("/{crew_id}/join", response_model=CrewResponse)
def join_crew(crew_id: int, current_user: CurrentUser, db: DbSession) -> CrewResponse:
    crew = db.get(Crew, crew_id)
    if crew is None or not crew.is_active:
        raise HTTPException(status_code=404, detail="Crew not found")
    if crew.join_policy == CrewJoinPolicy.INVITE_ONLY:
        raise HTTPException(status_code=403, detail="This crew requires an invitation")
    member = membership(db, crew_id, current_user.id)
    target_status = (
        CrewMemberStatus.ACTIVE
        if crew.join_policy == CrewJoinPolicy.OPEN
        else CrewMemberStatus.PENDING
    )
    if member is None:
        member = CrewMember(
            crew_id=crew_id,
            user_id=current_user.id,
            role=CrewMemberRole.MEMBER,
        )
        db.add(member)
    member.status = target_status
    member.joined_at = utcnow() if target_status == CrewMemberStatus.ACTIVE else None
    db.commit()
    return crew_response(db, crew, current_user.id)


@router.get("/{crew_id}/members", response_model=list[CrewMemberResponse])
def list_members(
    crew_id: int, current_user: CurrentUser, db: DbSession
) -> list[CrewMemberResponse]:
    require_active_member(db, crew_id, current_user.id)
    rows = list(db.execute(
        select(CrewMember, User)
        .join(User, User.id == CrewMember.user_id)
        .where(CrewMember.crew_id == crew_id)
        .order_by(CrewMember.status, CrewMember.role, CrewMember.created_at)
    ))
    return [CrewMemberResponse(
        user_id=user.id,
        nickname=user.nickname,
        role=member.role.value,
        status=member.status,
        joined_at=member.joined_at,
    ) for member, user in rows]


@router.delete("/{crew_id}/members/me", status_code=status.HTTP_204_NO_CONTENT)
def leave_crew(crew_id: int, current_user: CurrentUser, db: DbSession) -> None:
    member = require_active_member(db, crew_id, current_user.id)
    if member.role == CrewMemberRole.OWNER:
        raise HTTPException(status_code=409, detail="Crew owner cannot leave the crew")
    member.status = CrewMemberStatus.LEFT
    db.commit()


@router.patch("/{crew_id}/members/{user_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
def approve_member(
    crew_id: int,
    user_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    require_manager(db, crew_id, current_user.id)
    member = membership(db, crew_id, user_id)
    if member is None or member.status != CrewMemberStatus.PENDING:
        raise HTTPException(status_code=404, detail="Pending member not found")
    member.status = CrewMemberStatus.ACTIVE
    member.joined_at = utcnow()
    db.commit()


@router.post("/{crew_id}/invitations", response_model=InvitationResponse)
def create_invitation(
    crew_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> InvitationResponse:
    require_manager(db, crew_id, current_user.id)
    token = secrets.token_urlsafe(32)
    expires_at = utcnow() + timedelta(days=7)
    db.add(
        CrewInvitation(
            crew_id=crew_id,
            invited_by_user_id=current_user.id,
            token_hash=hash_token(token),
            expires_at=expires_at,
        )
    )
    db.commit()
    return InvitationResponse(token=token, expires_at=expires_at)


@router.post("/invitations/accept", response_model=CrewResponse)
def accept_invitation(
    payload: InvitationAccept,
    current_user: CurrentUser,
    db: DbSession,
) -> CrewResponse:
    invitation = db.scalar(
        select(CrewInvitation).where(CrewInvitation.token_hash == hash_token(payload.token))
    )
    if invitation is None or invitation.used_at is not None or invitation.expires_at <= utcnow():
        raise HTTPException(status_code=401, detail="Invitation is invalid or expired")
    member = membership(db, invitation.crew_id, current_user.id)
    if member is None:
        member = CrewMember(
            crew_id=invitation.crew_id,
            user_id=current_user.id,
            role=CrewMemberRole.MEMBER,
        )
        db.add(member)
    member.status = CrewMemberStatus.ACTIVE
    member.joined_at = utcnow()
    invitation.used_at = utcnow()
    db.commit()
    return crew_response(db, db.get(Crew, invitation.crew_id), current_user.id)


@router.get("/{crew_id}/messages", response_model=list[CrewMessageResponse])
def list_messages(
    crew_id: int,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = 100,
) -> list[CrewMessageResponse]:
    require_active_member(db, crew_id, current_user.id)
    rows = list(
        db.execute(
            select(CrewMessage, User)
            .join(User, User.id == CrewMessage.author_id)
            .where(CrewMessage.crew_id == crew_id)
            .order_by(CrewMessage.created_at.desc())
            .limit(min(max(limit, 1), 100))
        )
    )
    return [
        CrewMessageResponse(
            id=message.id,
            author_id=user.id,
            author_nickname=user.nickname,
            content=message.content,
            created_at=message.created_at,
        )
        for message, user in reversed(rows)
    ]


@router.post("/{crew_id}/messages", response_model=CrewMessageResponse, status_code=201)
def create_message(
    crew_id: int,
    payload: CrewMessageCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> CrewMessageResponse:
    require_active_member(db, crew_id, current_user.id)
    message = CrewMessage(crew_id=crew_id, author_id=current_user.id, content=payload.content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return CrewMessageResponse(
        id=message.id,
        author_id=current_user.id,
        author_nickname=current_user.nickname,
        content=message.content,
        created_at=message.created_at,
    )


def crew_course_response(course: CrewCourse) -> CrewCourseResponse:
    return CrewCourseResponse(
        id=course.id,
        crew_id=course.crew_id,
        name=course.name,
        start_name=course.start_name,
        start=Coordinate(latitude=course.start_latitude, longitude=course.start_longitude),
        destination_name=course.destination_name,
        destination=Coordinate(
            latitude=course.destination_latitude,
            longitude=course.destination_longitude,
        ),
        baseline_duration_seconds=course.baseline_duration_seconds,
        ranking_mode=course.ranking_mode,
        starts_at=course.starts_at,
        event_date=course.event_date,
    )


@router.get("/{crew_id}/courses", response_model=list[CrewCourseResponse])
def list_crew_courses(
    crew_id: int,
    current_user: CurrentUser,
    db: DbSession,
    event_date: date | None = None,
) -> list[CrewCourseResponse]:
    require_active_member(db, crew_id, current_user.id)
    target_date = event_date or datetime.now().date()
    courses = list(
        db.scalars(
            select(CrewCourse)
            .where(
                CrewCourse.crew_id == crew_id,
                CrewCourse.is_active.is_(True),
                or_(CrewCourse.event_date == target_date, CrewCourse.event_date.is_(None)),
            )
            .order_by(CrewCourse.starts_at.desc(), CrewCourse.id.desc())
        )
    )
    return [crew_course_response(course) for course in courses]


@router.post("/{crew_id}/courses", response_model=CrewCourseResponse, status_code=201)
def create_crew_course(
    crew_id: int,
    payload: CrewCourseCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> CrewCourseResponse:
    require_manager(db, crew_id, current_user.id)
    if payload.event_date < datetime.now().date():
        raise HTTPException(status_code=422, detail="event_date cannot be in the past")
    course = CrewCourse(
        crew_id=crew_id,
        created_by_user_id=current_user.id,
        name=payload.name,
        start_name=payload.start_name,
        start_latitude=payload.start.latitude,
        start_longitude=payload.start.longitude,
        destination_name=payload.destination_name,
        destination_latitude=payload.destination.latitude,
        destination_longitude=payload.destination.longitude,
        baseline_duration_seconds=payload.baseline_duration_seconds,
        ranking_mode=payload.ranking_mode,
        starts_at=payload.starts_at,
        event_date=payload.event_date,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return crew_course_response(course)


@router.put("/{crew_id}/daily-rankings", response_model=CrewDailyRankingResponse)
def upsert_daily_ranking(
    crew_id: int,
    payload: CrewDailyRankingUpsert,
    current_user: CurrentUser,
    db: DbSession,
) -> CrewDailyRankingResponse:
    require_manager(db, crew_id, current_user.id)
    if db.get(Course, payload.course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")
    item = db.scalar(select(CrewDailyCourseRanking).where(
        CrewDailyCourseRanking.crew_id == crew_id,
        CrewDailyCourseRanking.recommendation_date == payload.recommendation_date,
        CrewDailyCourseRanking.course_id == payload.course_id,
    ))
    if item is None:
        item = CrewDailyCourseRanking(
            crew_id=crew_id,
            course_id=payload.course_id,
            created_by_user_id=current_user.id,
            recommendation_date=payload.recommendation_date,
        )
        db.add(item)
    item.ranking_mode = payload.ranking_mode
    item.baseline_duration_seconds = payload.baseline_duration_seconds
    db.commit()
    db.refresh(item)
    return CrewDailyRankingResponse.model_validate(item, from_attributes=True)


@router.get("/{crew_id}/daily-rankings", response_model=list[CrewDailyRankingResponse])
def list_daily_rankings(
    crew_id: int,
    current_user: CurrentUser,
    db: DbSession,
    recommendation_date: date | None = None,
) -> list[CrewDailyRankingResponse]:
    require_active_member(db, crew_id, current_user.id)
    target_date = recommendation_date or datetime.now().date()
    items = list(db.scalars(select(CrewDailyCourseRanking).where(
        CrewDailyCourseRanking.crew_id == crew_id,
        CrewDailyCourseRanking.recommendation_date == target_date,
    )))
    return [CrewDailyRankingResponse.model_validate(item, from_attributes=True) for item in items]


@router.get("/{crew_id}/daily-rankings/{course_id}", response_model=RankingResponse)
def crew_daily_course_ranking(
    crew_id: int,
    course_id: int,
    current_user: CurrentUser,
    db: DbSession,
    recommendation_date: date | None = None,
) -> RankingResponse:
    require_active_member(db, crew_id, current_user.id)
    target_date = recommendation_date or datetime.now().date()
    config = db.scalar(select(CrewDailyCourseRanking).where(
        CrewDailyCourseRanking.crew_id == crew_id,
        CrewDailyCourseRanking.course_id == course_id,
        CrewDailyCourseRanking.recommendation_date == target_date,
    ))
    if config is None:
        raise HTTPException(status_code=404, detail="Crew daily ranking is not configured")
    active_member_ids = select(CrewMember.user_id).where(
        CrewMember.crew_id == crew_id,
        CrewMember.status == CrewMemberStatus.ACTIVE,
    )
    query = select(DriveRecord, User).join(User, User.id == DriveRecord.user_id).where(
        DriveRecord.course_id == course_id,
        DriveRecord.user_id.in_(active_member_ids),
        DriveRecord.status == RecordStatus.COMPLETED,
        DriveRecord.validation_status == RecordValidationStatus.VALID,
        DriveRecord.ranking_eligible.is_(True),
    )
    if config.ranking_mode == RankingMode.FASTEST:
        query = query.order_by(DriveRecord.duration_seconds.asc())
    else:
        query = query.order_by(
            func.abs(DriveRecord.duration_seconds - config.baseline_duration_seconds).asc(),
            DriveRecord.duration_seconds.asc(),
        )
    rows = list(db.execute(query.limit(100)))
    return RankingResponse(
        mode=config.ranking_mode,
        baseline_duration_seconds=config.baseline_duration_seconds,
        safety_notice="교통법규를 준수하고 기록 경쟁보다 안전 운전을 우선해 주세요.",
        items=[RankingItem(
            rank=index,
            user_id=user.id,
            nickname=user.nickname,
            duration_seconds=record.duration_seconds or 0,
            baseline_delta_seconds=(record.duration_seconds or 0) - (
                config.baseline_duration_seconds or record.duration_seconds or 0
            ),
        ) for index, (record, user) in enumerate(rows, start=1)],
    )
