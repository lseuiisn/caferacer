from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.api.routers.courses import course_response
from app.integrations.tmap import TmapClient, TmapError
from app.repositories.catalog import CatalogRepository
from app.schemas.recommendations import RecommendationItem, RecommendationRequest, RecommendationResponse

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
repository = CatalogRepository()


@router.post(
    "",
    response_model=RecommendationResponse,
    summary="조건 기반 드라이브 코스 추천",
    description="코스 조건과 카페 휴식 조건을 먼저 적용한 뒤, 현재 위치에서 코스 시작점까지의 TMAP 이동 시간을 포함해 왕복 시간 적합도를 계산합니다.",
)
async def recommend_courses(payload: RecommendationRequest, db: DbSession) -> RecommendationResponse:
    courses, _ = repository.list_courses(db, region=None, duration_minutes=payload.round_trip_minutes, moods=payload.moods, season=payload.season, difficulty=payload.difficulty, page=1, size=50)
    ids = [course.id for course in courses]
    cafe_counts = repository.course_cafe_counts(db, ids)
    moods = repository.course_moods(db, ids)
    client = TmapClient()
    items: list[RecommendationItem] = []
    for course in courses:
        start = repository.course_start_point(db, course.id)
        if start is None:
            continue
        linked_cafes = repository.course_cafes(db, course.id, parking_required=payload.filters.parking_required, price_ranges=payload.filters.price_ranges, tags=payload.filters.tags)
        if not linked_cafes:
            continue
        try:
            ingress = await client.estimate_car_route(start_latitude=payload.origin.latitude, start_longitude=payload.origin.longitude, end_latitude=float(start.latitude), end_longitude=float(start.longitude), start_name="origin", end_name=course.name)
        except TmapError as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="TMAP route estimate is unavailable") from error
        total_minutes = course.estimated_duration_minutes + round((ingress.duration_seconds * 2) / 60)
        if total_minutes > payload.round_trip_minutes:
            continue
        tag_map = repository.cafe_tags(db, [cafe.id for cafe, _ in linked_cafes])
        cafes = [{"id": cafe.id, "name": cafe.name, "address": cafe.address, "latitude": cafe.latitude, "longitude": cafe.longitude, "stop_order": stop_order, "tags": tag_map[cafe.id]} for cafe, stop_order in linked_cafes]
        time_score = max(0, 50 - round((payload.round_trip_minutes - total_minutes) / max(payload.round_trip_minutes, 1) * 50))
        score = int(min(100, time_score + min(25, float(course.drive_suitability_score) * 5) + min(15, len(cafes) * 5) + 10))
        reasons = [f"왕복 {total_minutes}분 조건 충족", f"{course.difficulty} 난이도 드라이브", f"추천 카페 {len(cafes)}곳 포함"]
        if payload.filters.parking_required:
            reasons.append("주차 가능한 카페 포함")
        items.append(RecommendationItem(course=course_response(course, cafe_count=cafe_counts.get(course.id, 0), moods=moods[course.id]), cafes=cafes, estimated_round_trip_minutes=total_minutes, estimated_distance_meters=course.estimated_distance_meters + ingress.distance_meters * 2, score=score, reason=reasons))
    return RecommendationResponse(items=sorted(items, key=lambda item: item.score, reverse=True))
