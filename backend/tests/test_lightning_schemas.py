from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.main import app
from app.schemas.drive_records import DriveRecordCreate
from app.schemas.lightning_courses import (
    CrewDailyRankingUpsert,
    LightningCourseCreate,
)


def coordinate() -> dict[str, float]:
    return {"latitude": 37.5665, "longitude": 126.9780}


def test_drive_record_requires_exactly_one_target() -> None:
    with pytest.raises(ValidationError):
        DriveRecordCreate(started_at=datetime.now())
    with pytest.raises(ValidationError):
        DriveRecordCreate(
            course_id=1,
            lightning_course_id=2,
            started_at=datetime.now(),
        )
    payload = DriveRecordCreate(lightning_course_id=2, started_at=datetime.now())
    assert payload.lightning_course_id == 2


def test_lightning_course_always_requires_baseline() -> None:
    base = {
        "name": "한강 번개",
        "event_date": date.today(),
        "start_name": "출발",
        "start": coordinate(),
        "destination_name": "도착",
        "destination": coordinate(),
        "ranking_mode": "fastest",
    }
    with pytest.raises(ValidationError):
        LightningCourseCreate.model_validate(base)
    payload = LightningCourseCreate.model_validate(
        {**base, "baseline_duration_seconds": 3600}
    )
    assert payload.baseline_duration_seconds == 3600


def test_closest_crew_ranking_requires_baseline() -> None:
    with pytest.raises(ValidationError):
        CrewDailyRankingUpsert(
            course_id=1,
            recommendation_date=date.today(),
            ranking_mode="closest_to_baseline",
        )


def test_openapi_contains_lightning_and_cancel_paths() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/lightning-courses" in paths
    assert "/api/v1/drive-records/{record_id}/cancel" in paths
    assert "/api/v1/crews/{crew_id}/daily-rankings/{course_id}" in paths
