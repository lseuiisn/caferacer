from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import RecordStatus, RecordValidationStatus


class DriveRecordCreate(BaseModel):
    course_id: int | None = Field(default=None, gt=0)
    crew_course_id: int | None = Field(default=None, gt=0)
    lightning_course_id: int | None = Field(default=None, gt=0)
    started_at: datetime

    @model_validator(mode="after")
    def validate_target(self) -> "DriveRecordCreate":
        if sum(value is not None for value in (
            self.course_id, self.crew_course_id, self.lightning_course_id
        )) != 1:
            raise ValueError("exactly one drive target is required")
        return self


class DrivePointCreate(BaseModel):
    sequence: int = Field(ge=0)
    recorded_at: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0, le=1000)
    speed_mps: float | None = Field(default=None, ge=0, le=150)
    heading_degrees: float | None = Field(default=None, ge=0, lt=360)


class DrivePointBatch(BaseModel):
    points: list[DrivePointCreate] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_sequence(self) -> "DrivePointBatch":
        sequences = [point.sequence for point in self.points]
        if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
            raise ValueError("point sequences must be unique and ascending")
        return self


class DriveRecordComplete(BaseModel):
    completed_at: datetime


class DriveRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    course_id: int | None
    crew_course_id: int | None
    lightning_course_id: int | None
    status: RecordStatus
    validation_status: RecordValidationStatus
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    distance_meters: int
    baseline_delta_seconds: int | None
    path_coverage_percent: float
    ranking_eligible: bool


class DrivePointBatchResponse(BaseModel):
    accepted_count: int
    last_sequence: int


class DriveRecordPage(BaseModel):
    items: list[DriveRecordResponse]
    page: int
    size: int
    total: int
