from dataclasses import dataclass
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from app.models.catalog import CourseNavigationAnchor, CoursePath
from app.models.drive import DriveRecordPoint

EARTH_RADIUS_METERS = 6_371_000
MAX_USABLE_ACCURACY_METERS = 50
PATH_MATCH_RADIUS_METERS = 100
MINIMUM_PATH_COVERAGE_PERCENT = 80


def distance_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    lat_a = radians(latitude_a)
    lat_b = radians(latitude_b)
    delta_lat = lat_b - lat_a
    delta_lon = radians(longitude_b - longitude_a)
    value = sin(delta_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * asin(sqrt(value))


def usable_points(points: list[DriveRecordPoint]) -> list[DriveRecordPoint]:
    return [
        point
        for point in points
        if point.accuracy_meters is None
        or float(point.accuracy_meters) <= MAX_USABLE_ACCURACY_METERS
    ]


def travelled_distance(points: list[DriveRecordPoint]) -> int:
    valid_points = usable_points(points)
    return round(
        sum(
            distance_meters(
                float(previous.latitude),
                float(previous.longitude),
                float(current.latitude),
                float(current.longitude),
            )
            for previous, current in zip(valid_points, valid_points[1:], strict=False)
        )
    )


def path_coverage(points: list[DriveRecordPoint], path: list[CoursePath]) -> float:
    valid_points = usable_points(points)
    if not valid_points or not path:
        return 0
    matched = sum(
        any(
            distance_meters(
                float(path_point.latitude),
                float(path_point.longitude),
                float(point.latitude),
                float(point.longitude),
            )
            <= PATH_MATCH_RADIUS_METERS
            for point in valid_points
        )
        for path_point in path
    )
    return round(matched / len(path) * 100, 2)


@dataclass(frozen=True)
class AnchorMatch:
    anchor: CourseNavigationAnchor
    passed_at: datetime
    minimum_distance_meters: float


def matched_anchors(
    points: list[DriveRecordPoint], anchors: list[CourseNavigationAnchor]
) -> list[AnchorMatch]:
    valid_points = usable_points(points)
    result: list[AnchorMatch] = []
    for anchor in anchors:
        candidates = [
            (
                distance_meters(
                    float(anchor.latitude),
                    float(anchor.longitude),
                    float(point.latitude),
                    float(point.longitude),
                ),
                point.recorded_at,
            )
            for point in valid_points
        ]
        if not candidates:
            continue
        minimum_distance, passed_at = min(candidates, key=lambda candidate: candidate[0])
        if minimum_distance <= anchor.pass_radius_meters:
            result.append(
                AnchorMatch(
                    anchor=anchor,
                    passed_at=passed_at,
                    minimum_distance_meters=round(minimum_distance, 2),
                )
            )
    return result


def is_ranking_eligible(
    coverage_percent: float,
    matched_anchor_count: int,
    total_anchor_count: int,
) -> bool:
    return (
        total_anchor_count > 0
        and matched_anchor_count == total_anchor_count
        and coverage_percent >= MINIMUM_PATH_COVERAGE_PERCENT
    )
