from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import RankingMode
from app.schemas.recommendations import Coordinate


class LightningCourseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    event_date: date
    start_name: str = Field(min_length=1, max_length=120)
    start: Coordinate
    destination_name: str = Field(min_length=1, max_length=120)
    destination: Coordinate
    ranking_mode: RankingMode
    baseline_duration_seconds: int = Field(gt=0, le=86400)


class LightningCourseResponse(BaseModel):
    id: int
    created_by_user_id: int
    name: str
    event_date: date
    start_name: str
    start: Coordinate
    destination_name: str
    destination: Coordinate
    ranking_mode: RankingMode
    baseline_duration_seconds: int | None
    participant_count: int
    joined_by_me: bool
    created_at: datetime


class LightningCoursePage(BaseModel):
    items: list[LightningCourseResponse]
    page: int
    size: int
    total: int


class CrewDailyRankingUpsert(BaseModel):
    course_id: int = Field(gt=0)
    recommendation_date: date
    ranking_mode: RankingMode
    baseline_duration_seconds: int | None = Field(default=None, gt=0, le=86400)

    @model_validator(mode="after")
    def validate_baseline(self) -> "CrewDailyRankingUpsert":
        if self.ranking_mode == RankingMode.CLOSEST_TO_BASELINE and self.baseline_duration_seconds is None:
            raise ValueError("baseline_duration_seconds is required for closest_to_baseline")
        return self


class CrewDailyRankingResponse(BaseModel):
    id: int
    crew_id: int
    course_id: int
    recommendation_date: date
    ranking_mode: RankingMode
    baseline_duration_seconds: int | None
