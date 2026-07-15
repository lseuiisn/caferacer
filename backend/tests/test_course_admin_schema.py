import pytest
from pydantic import ValidationError

from app.schemas.course_admin import CourseUpsert


def payload(waypoint_count: int) -> dict:
    anchors = [
        {
            "sequence": 0,
            "name": "start",
            "anchor_type": "start",
            "latitude": 37.0,
            "longitude": 127.0,
        }
    ]
    anchors.extend(
        {
            "sequence": index,
            "name": f"waypoint-{index}",
            "anchor_type": "waypoint",
            "latitude": 37.0 + index / 1000,
            "longitude": 127.0,
        }
        for index in range(1, waypoint_count + 1)
    )
    anchors.append(
        {
            "sequence": len(anchors),
            "name": "destination",
            "anchor_type": "destination",
            "latitude": 37.1,
            "longitude": 127.1,
        }
    )
    return {
        "name": "test course",
        "region": "경기도",
        "estimated_duration_minutes": 60,
        "estimated_distance_meters": 10000,
        "path": [
            {"sequence": 0, "latitude": 37.0, "longitude": 127.0},
            {"sequence": 1, "latitude": 37.1, "longitude": 127.1},
        ],
        "navigation_anchors": anchors,
    }


def test_ten_waypoints_are_allowed() -> None:
    course = CourseUpsert.model_validate(payload(10))
    assert len(course.navigation_anchors) == 12


def test_more_than_ten_waypoints_are_rejected() -> None:
    with pytest.raises(ValidationError):
        CourseUpsert.model_validate(payload(11))
