"""Create or update a course from a GPX track.

Example:
python -m scripts.import_course --gpx data/raw_paths/gapyeong.gpx --name "가평 코스" \
  --region "경기도 가평" --duration 120 --moods riverside,winding \
  --cafe-ids 1 --waypoint-indexes 120,350 --apply
"""

import argparse
import json
import re
from math import ceil
from pathlib import Path
from xml.etree import ElementTree

from sqlalchemy import select

from app.api.routers.admin_courses import save_course
from app.core.database import SessionLocal
from app.models.catalog import Course
from app.models.enums import NavigationAnchorType
from app.schemas.course_admin import CourseUpsert
from app.services.drive_tracking import distance_meters
from scripts.seed_catalog import seed_course_tags


def parse_gpx(path: Path) -> list[tuple[float, float]]:
    root = ElementTree.parse(path).getroot()
    points = [
        (float(element.attrib["lat"]), float(element.attrib["lon"]))
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "trkpt"
    ]
    if len(points) < 2:
        raise ValueError("GPX must contain at least two track points")
    return points


def downsample(points: list[tuple[float, float]], maximum: int = 2000) -> list[tuple[float, float]]:
    if len(points) <= maximum:
        return points
    step = ceil(len(points) / maximum)
    sampled = points[::step]
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])
    return sampled


def route_distance(points: list[tuple[float, float]]) -> int:
    return round(
        sum(
            distance_meters(*previous, *current)
            for previous, current in zip(points, points[1:], strict=False)
        )
    )


def csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_payload(args: argparse.Namespace) -> CourseUpsert:
    points = downsample(parse_gpx(args.gpx))
    waypoint_indexes = [int(value) for value in csv_values(args.waypoint_indexes)]
    if len(waypoint_indexes) > 10:
        raise ValueError("At most 10 waypoint indexes are allowed")
    if any(index <= 0 or index >= len(points) - 1 for index in waypoint_indexes):
        raise ValueError(f"Waypoint indexes must be between 1 and {len(points) - 2}")

    anchors = [
        {
            "sequence": 0,
            "name": f"{args.name} 시작점",
            "anchor_type": NavigationAnchorType.START,
            "latitude": points[0][0],
            "longitude": points[0][1],
            "pass_radius_meters": args.anchor_radius,
        }
    ]
    anchors.extend(
        {
            "sequence": sequence,
            "name": f"경유지 {sequence}",
            "anchor_type": NavigationAnchorType.WAYPOINT,
            "latitude": points[index][0],
            "longitude": points[index][1],
            "pass_radius_meters": args.anchor_radius,
        }
        for sequence, index in enumerate(waypoint_indexes, start=1)
    )
    anchors.append(
        {
            "sequence": len(anchors),
            "name": f"{args.name} 도착점",
            "anchor_type": NavigationAnchorType.DESTINATION,
            "latitude": points[-1][0],
            "longitude": points[-1][1],
            "pass_radius_meters": args.anchor_radius,
        }
    )
    return CourseUpsert(
        name=args.name,
        description=args.description,
        region=args.region,
        estimated_duration_minutes=args.duration,
        estimated_distance_meters=args.distance or route_distance(points),
        difficulty=args.difficulty,
        recommended_season=args.season,
        recommended_time=args.time,
        drive_suitability_score=args.score,
        moods=csv_values(args.moods),
        cafe_ids=[int(value) for value in csv_values(args.cafe_ids)],
        path=[
            {
                "sequence": index,
                "latitude": latitude,
                "longitude": longitude,
                "road_type": "unknown",
            }
            for index, (latitude, longitude) in enumerate(points)
        ],
        navigation_anchors=anchors,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="GPX 코스를 WayPoint 데이터로 변환")
    parser.add_argument("--gpx", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--duration", type=int, required=True)
    parser.add_argument("--distance", type=int)
    parser.add_argument("--description")
    parser.add_argument("--difficulty", default="normal")
    parser.add_argument("--season", default="all")
    parser.add_argument("--time", default="day")
    parser.add_argument("--score", type=float, default=0)
    parser.add_argument("--moods", default="")
    parser.add_argument("--cafe-ids", default="")
    parser.add_argument("--waypoint-indexes", default="")
    parser.add_argument("--anchor-radius", type=int, default=100)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    output = args.output or Path("data/generated_courses") / (
        re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", args.name).strip("_") + ".json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Validated course JSON: {output}")

    if args.apply:
        # GPX 운영 도구는 기본 분위기 태그가 없는 신규 DB에서도 바로 사용할 수 있다.
        seed_course_tags()
        db = SessionLocal()
        try:
            course = db.scalar(select(Course).where(Course.name == payload.name))
            course = course or Course(
                name=payload.name,
                region=payload.region,
                estimated_duration_minutes=payload.estimated_duration_minutes,
                estimated_distance_meters=payload.estimated_distance_meters,
            )
            result = save_course(db, course, payload)
            print(f"Applied course id={result.id}, path_points={result.path_point_count}")
        finally:
            db.close()


if __name__ == "__main__":
    main()
