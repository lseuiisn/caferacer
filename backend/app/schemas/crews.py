from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import CrewJoinPolicy, CrewMemberStatus, CrewVisibility, RankingMode
from app.schemas.recommendations import Coordinate


class CrewCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    visibility: CrewVisibility
    join_policy: CrewJoinPolicy


class CrewResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str | None
    image_url: str | None
    visibility: CrewVisibility
    join_policy: CrewJoinPolicy
    member_count: int
    my_status: CrewMemberStatus | None


class CrewPage(BaseModel):
    items: list[CrewResponse]
    page: int
    size: int
    total: int


class InvitationResponse(BaseModel):
    token: str
    expires_at: datetime


class InvitationAccept(BaseModel):
    token: str = Field(min_length=32, max_length=128)


class CrewMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class CrewMessageResponse(BaseModel):
    id: int
    author_id: int
    author_nickname: str | None
    content: str
    created_at: datetime


class CrewCourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    start_name: str = Field(min_length=1, max_length=120)
    start: Coordinate
    destination_name: str = Field(min_length=1, max_length=120)
    destination: Coordinate
    baseline_duration_seconds: int = Field(gt=0, le=86400)
    ranking_mode: RankingMode
    starts_at: datetime | None = None
    event_date: date


class CrewCourseResponse(BaseModel):
    id: int
    crew_id: int
    name: str
    start_name: str
    start: Coordinate
    destination_name: str
    destination: Coordinate
    baseline_duration_seconds: int
    ranking_mode: RankingMode
    starts_at: datetime | None
    event_date: date | None


class CrewMemberResponse(BaseModel):
    user_id: int
    nickname: str | None
    role: str
    status: CrewMemberStatus
    joined_at: datetime | None


class RankingItem(BaseModel):
    rank: int
    user_id: int
    nickname: str | None
    duration_seconds: int
    baseline_delta_seconds: int


class RankingResponse(BaseModel):
    mode: RankingMode
    baseline_duration_seconds: int | None = None
    safety_notice: str
    items: list[RankingItem]
