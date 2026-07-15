"""Import operator-verified cafe and course data from JSON.

The importer is intentionally explicit: it receives only reviewed data and never crawls or
publishes third-party content by itself.
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.catalog import (
    Cafe,
    CafeDataSource,
    CafeTag,
    CafeTagAssignment,
    Course,
    CourseCafe,
    CourseNavigationAnchor,
    CoursePath,
    CourseTag,
    CourseTagAssignment,
)
from app.models.enums import NavigationAnchorType

DEFAULT_TAGS = [
    ("riverside", "강변", "view"),
    ("ocean_view", "오션뷰", "view"),
    ("city_view", "도시뷰", "view"),
    ("quiet", "조용한", "mood"),
    ("large_space", "대형 카페", "facility"),
    ("pet_friendly", "반려동물 동반", "facility"),
    ("kids_friendly", "키즈 프렌들리", "facility"),
    ("scenic_drive", "경치 좋은 드라이브", "drive"),
]

DEFAULT_COURSE_TAGS = [
    ("scenic", "경치 좋은 드라이브", "mood"),
    ("riverside", "강변 드라이브", "mood"),
    ("coastal", "해안 드라이브", "mood"),
    ("mountain", "산길 드라이브", "mood"),
    ("winding", "와인딩 드라이브", "mood"),
]


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def seed_tags() -> dict[str, CafeTag]:
    db = SessionLocal()
    try:
        existing = {tag.code: tag for tag in db.scalars(select(CafeTag))}
        for code, display_name, category in DEFAULT_TAGS:
            if code not in existing:
                tag = CafeTag(code=code, display_name=display_name, category=category)
                db.add(tag)
                existing[code] = tag
        db.commit()
        return existing
    finally:
        db.close()


def seed_course_tags() -> dict[str, CourseTag]:
    db = SessionLocal()
    try:
        existing = {tag.code: tag for tag in db.scalars(select(CourseTag))}
        for code, display_name, category in DEFAULT_COURSE_TAGS:
            if code not in existing:
                tag = CourseTag(code=code, display_name=display_name, category=category)
                db.add(tag)
                existing[code] = tag
        db.commit()
        return existing
    finally:
        db.close()


def load_catalog(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        tags = {tag.code: tag for tag in db.scalars(select(CafeTag))}
        course_tags = {tag.code: tag for tag in db.scalars(select(CourseTag))}
        for cafe_data in payload.get("cafes", []):
            source_url = cafe_data["source_url"]
            existing = db.scalar(select(Cafe).where(Cafe.name == cafe_data["name"], Cafe.address == cafe_data["address"]))
            cafe = existing or Cafe(name=cafe_data["name"], address=cafe_data["address"])
            cafe.latitude = cafe_data["latitude"]
            cafe.longitude = cafe_data["longitude"]
            cafe.phone_number = cafe_data.get("phone_number")
            cafe.business_hours = cafe_data.get("business_hours")
            cafe.price_range = cafe_data.get("price_range")
            cafe.parking_available = cafe_data.get("parking_available", False)
            cafe.is_active = True
            cafe.verified_at = utcnow()
            db.add(cafe)
            db.flush()
            if not db.scalar(select(CafeDataSource).where(CafeDataSource.cafe_id == cafe.id, CafeDataSource.source_url == source_url)):
                db.add(CafeDataSource(cafe_id=cafe.id, source_type="official", source_url=source_url, collected_at=utcnow(), verified_at=utcnow()))
            for tag_code in cafe_data.get("tags", []):
                if tag_code not in tags:
                    raise ValueError(f"Unknown tag code: {tag_code}")
                if not db.get(CafeTagAssignment, {"cafe_id": cafe.id, "tag_id": tags[tag_code].id}):
                    db.add(CafeTagAssignment(cafe_id=cafe.id, tag_id=tags[tag_code].id))

        for course_data in payload.get("courses", []):
            course = db.scalar(select(Course).where(Course.name == course_data["name"]))
            course = course or Course(name=course_data["name"], region=course_data["region"], estimated_duration_minutes=0, estimated_distance_meters=0)
            course.region = course_data["region"]
            course.description = course_data.get("description", course_data.get("summary"))
            course.estimated_duration_minutes = course_data["estimated_duration_minutes"]
            course.estimated_distance_meters = course_data["estimated_distance_meters"]
            course.drive_suitability_score = course_data.get("drive_suitability_score", 0)
            course.difficulty = course_data.get("difficulty", "normal")
            course.recommended_season = course_data.get("recommended_season", "all")
            course.recommended_time = course_data.get("recommended_time", "day")
            course.thumbnail_url = course_data.get("thumbnail_url")
            course.is_active = True
            db.add(course)
            db.flush()
            if not db.scalar(select(CoursePath).where(CoursePath.course_id == course.id)):
                for waypoint in course_data.get("path", course_data.get("waypoints", [])):
                    db.add(CoursePath(course_id=course.id, sequence=waypoint["sequence"], latitude=waypoint["latitude"], longitude=waypoint["longitude"], road_name=waypoint.get("road_name", waypoint.get("name")), road_type=waypoint.get("road_type", "unknown")))
            if not db.scalar(
                select(CourseNavigationAnchor).where(
                    CourseNavigationAnchor.course_id == course.id
                )
            ):
                for anchor in course_data.get("navigation_anchors", []):
                    db.add(
                        CourseNavigationAnchor(
                            course_id=course.id,
                            sequence=anchor["sequence"],
                            name=anchor["name"],
                            anchor_type=NavigationAnchorType(anchor["anchor_type"]),
                            latitude=anchor["latitude"],
                            longitude=anchor["longitude"],
                            pass_radius_meters=anchor.get("pass_radius_meters", 100),
                        )
                    )
            for stop_order, cafe_name in enumerate(course_data.get("cafe_names", []), start=1):
                cafe = db.scalar(select(Cafe).where(Cafe.name == cafe_name))
                if cafe is None:
                    raise ValueError(f"Course cafe not found: {cafe_name}")
                if not db.get(CourseCafe, {"course_id": course.id, "cafe_id": cafe.id}):
                    db.add(CourseCafe(course_id=course.id, cafe_id=cafe.id, stop_order=stop_order, recommendation_weight=1))
            for tag_code in course_data.get("moods", []):
                if tag_code not in course_tags:
                    raise ValueError(f"Unknown course mood code: {tag_code}")
                if not db.get(CourseTagAssignment, {"course_id": course.id, "tag_id": course_tags[tag_code].id}):
                    db.add(CourseTagAssignment(course_id=course.id, tag_id=course_tags[tag_code].id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, help="검수 완료한 카페·코스 JSON 파일")
    parser.add_argument("--tags-only", action="store_true", help="기본 태그만 생성")
    args = parser.parse_args()
    seed_tags()
    seed_course_tags()
    if args.path:
        load_catalog(args.path)
    elif not args.tags_only:
        parser.error("--path 또는 --tags-only 중 하나가 필요합니다.")
