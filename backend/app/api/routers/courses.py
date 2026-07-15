from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.integrations.tmap import TmapClient, TmapError
from app.repositories.catalog import CatalogRepository
from app.schemas.catalog import CourseCafeResponse, CourseDetail, CourseListItem, CourseNavigationAnchorResponse, CoursePage, CoursePathResponse, CoursePolyline, PageMeta
from app.schemas.recommendations import (
    Coordinate,
    CourseNavigationRequest,
    CourseNavigationResponse,
    NavigationAnchorResponse,
)

router = APIRouter(prefix="/courses", tags=["courses"])
repository = CatalogRepository()


def course_response(course, *, cafe_count: int = 0, moods: list[str] | None = None) -> CourseListItem:
    return CourseListItem(id=course.id, name=course.name, description=course.description, region=course.region, estimated_duration_minutes=course.estimated_duration_minutes, estimated_distance_meters=course.estimated_distance_meters, difficulty=course.difficulty, recommended_season=course.recommended_season, recommended_time=course.recommended_time, thumbnail_url=course.thumbnail_url, cafe_count=cafe_count, moods=moods or [])


def course_cafe_responses(db: DbSession, course_id: int) -> list[CourseCafeResponse]:
    linked_cafes = repository.course_cafes(db, course_id)
    tag_map = repository.cafe_tags(db, [cafe.id for cafe, _ in linked_cafes])
    return [CourseCafeResponse(id=cafe.id, name=cafe.name, address=cafe.address, latitude=cafe.latitude, longitude=cafe.longitude, stop_order=stop_order, tags=tag_map[cafe.id]) for cafe, stop_order in linked_cafes]


@router.get(
    "",
    response_model=CoursePage,
    summary="드라이브 코스 목록 조회",
    description="카페가 아닌 드라이브 코스를 우선 조회합니다. `mood`를 여러 번 전달하면 모든 분위기 태그를 만족하는 코스만 반환합니다.",
)
def list_courses(db: DbSession, region: str | None = None, duration_minutes: Annotated[int | None, Query(ge=1)] = None, mood: Annotated[list[str] | None, Query()] = None, season: str | None = None, difficulty: str | None = None, page: Annotated[int, Query(ge=1)] = 1, size: Annotated[int, Query(ge=1, le=50)] = 20) -> CoursePage:
    courses, total = repository.list_courses(db, region=region, duration_minutes=duration_minutes, moods=mood, season=season, difficulty=difficulty, page=page, size=size)
    ids = [course.id for course in courses]
    counts = repository.course_cafe_counts(db, ids)
    moods = repository.course_moods(db, ids)
    return CoursePage(items=[course_response(course, cafe_count=counts.get(course.id, 0), moods=moods[course.id]) for course in courses], meta=PageMeta(page=page, size=size, total=total))


@router.get(
    "/{course_id}",
    response_model=CourseDetail,
    summary="드라이브 코스 상세 조회",
    description="우리 서비스가 관리하는 Path 폴리라인과 순서가 있는 카페 휴식 포인트를 함께 반환합니다.",
)
def get_course(course_id: int, db: DbSession) -> CourseDetail:
    course = repository.get_course(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    paths = repository.course_paths(db, course_id)
    if not paths:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Course path is not configured")
    anchors = repository.course_navigation_anchors(db, course_id)
    return CourseDetail(
        **course_response(course, cafe_count=len(repository.course_cafes(db, course_id)), moods=repository.course_moods(db, [course_id])[course_id]).model_dump(),
        path=CoursePolyline(coordinates=[(point.latitude, point.longitude) for point in paths]),
        path_points=[CoursePathResponse.model_validate(point) for point in paths],
        cafes=course_cafe_responses(db, course_id),
        navigation_anchors=[
            CourseNavigationAnchorResponse(
                sequence=anchor.sequence,
                name=anchor.name,
                anchor_type=anchor.anchor_type.value,
                latitude=anchor.latitude,
                longitude=anchor.longitude,
                pass_radius_meters=anchor.pass_radius_meters,
            )
            for anchor in anchors
        ],
    )


@router.post(
    "/{course_id}/navigation",
    response_model=CourseNavigationResponse,
    summary="외부 TMAP 실행용 코스 안내 정보 생성",
    description=(
        "현재 위치에서 코스 시작점까지의 예상 정보와 TMAP에 전달할 시작점·핵심 경유지·"
        "도착점을 반환합니다. TMAP 실행 전 DriveRecord를 만들고 백그라운드 GPS 권한을 "
        "확인해야 합니다. 전체 코스 검증에는 우리 DB의 CoursePath를 사용합니다."
    ),
)
async def create_course_navigation(course_id: int, payload: CourseNavigationRequest, db: DbSession) -> CourseNavigationResponse:
    course = repository.get_course(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    start = repository.course_start_point(db, course_id)
    if start is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Course start point is not configured")
    anchors = repository.course_navigation_anchors(db, course_id)
    if not anchors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course navigation anchors are not configured",
        )
    try:
        route = await TmapClient().estimate_car_route(start_latitude=payload.origin.latitude, start_longitude=payload.origin.longitude, end_latitude=float(start.latitude), end_longitude=float(start.longitude), start_name="origin", end_name=course.name)
    except TmapError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="TMAP navigation is unavailable") from error
    return CourseNavigationResponse(
        distance_meters=route.distance_meters,
        duration_seconds=route.duration_seconds,
        start_point=Coordinate(latitude=start.latitude, longitude=start.longitude),
        anchors=[
            NavigationAnchorResponse(
                sequence=anchor.sequence,
                name=anchor.name,
                anchor_type=anchor.anchor_type.value,
                latitude=anchor.latitude,
                longitude=anchor.longitude,
                pass_radius_meters=anchor.pass_radius_meters,
            )
            for anchor in anchors
        ],
    )
