from datetime import datetime, timedelta
from unittest import TestCase

from app.models.catalog import CourseNavigationAnchor, CoursePath
from app.models.drive import DriveRecordPoint
from app.models.enums import NavigationAnchorType
from app.services.drive_tracking import (
    is_ranking_eligible,
    matched_anchors,
    path_coverage,
    travelled_distance,
)


def point(sequence: int, latitude: float, longitude: float) -> DriveRecordPoint:
    return DriveRecordPoint(
        drive_record_id=1,
        sequence=sequence,
        recorded_at=datetime(2026, 7, 15) + timedelta(seconds=sequence),
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=5,
    )


class DriveTrackingTest(TestCase):
    def test_drive_completion_metrics(self) -> None:
        points = [point(0, 37.0, 127.0), point(1, 37.001, 127.0)]
        path = [
            CoursePath(course_id=1, sequence=0, latitude=37.0, longitude=127.0),
            CoursePath(course_id=1, sequence=1, latitude=37.001, longitude=127.0),
        ]
        anchors = [
            CourseNavigationAnchor(
                id=1,
                course_id=1,
                sequence=0,
                name="start",
                anchor_type=NavigationAnchorType.START,
                latitude=37.0,
                longitude=127.0,
                pass_radius_meters=100,
            ),
            CourseNavigationAnchor(
                id=2,
                course_id=1,
                sequence=1,
                name="destination",
                anchor_type=NavigationAnchorType.DESTINATION,
                latitude=37.001,
                longitude=127.0,
                pass_radius_meters=100,
            ),
        ]

        coverage = path_coverage(points, path)
        matches = matched_anchors(points, anchors)

        self.assertTrue(100 <= travelled_distance(points) <= 120)
        self.assertEqual(coverage, 100)
        self.assertEqual(len(matches), 2)
        self.assertTrue(is_ranking_eligible(coverage, len(matches), len(anchors)))

    def test_inaccurate_points_are_not_used(self) -> None:
        inaccurate = point(0, 37.0, 127.0)
        inaccurate.accuracy_meters = 100
        path = [CoursePath(course_id=1, sequence=0, latitude=37.0, longitude=127.0)]

        self.assertEqual(path_coverage([inaccurate], path), 0)
