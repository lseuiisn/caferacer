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
from app.models.catalog import Cafe, CafeDataSource, CafeTag, CafeTagAssignment, Course, CourseCafe, CourseWaypoint

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


def load_catalog(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        tags = {tag.code: tag for tag in db.scalars(select(CafeTag))}
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
            course.summary = course_data.get("summary")
            course.estimated_duration_minutes = course_data["estimated_duration_minutes"]
            course.estimated_distance_meters = course_data["estimated_distance_meters"]
            course.drive_suitability_score = course_data.get("drive_suitability_score", 0)
            course.is_active = True
            db.add(course)
            db.flush()
            if not db.scalar(select(CourseWaypoint).where(CourseWaypoint.course_id == course.id)):
                for waypoint in course_data.get("waypoints", []):
                    db.add(CourseWaypoint(course_id=course.id, **waypoint))
            for cafe_name in course_data.get("cafe_names", []):
                cafe = db.scalar(select(Cafe).where(Cafe.name == cafe_name))
                if cafe is None:
                    raise ValueError(f"Course cafe not found: {cafe_name}")
                if not db.get(CourseCafe, {"course_id": course.id, "cafe_id": cafe.id}):
                    db.add(CourseCafe(course_id=course.id, cafe_id=cafe.id, recommendation_weight=1))
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
    if args.path:
        load_catalog(args.path)
    elif not args.tags_only:
        parser.error("--path 또는 --tags-only 중 하나가 필요합니다.")
