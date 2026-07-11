from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.repositories.catalog import CatalogRepository
from app.schemas.catalog import (
    CourseCafeResponse,
    CourseDetail,
    CourseListItem,
    CoursePage,
    CourseWaypointResponse,
    PageMeta,
)

router = APIRouter(prefix="/courses", tags=["courses"])
repository = CatalogRepository()


def course_response(course) -> CourseListItem:
    return CourseListItem.model_validate(course)


@router.get("", response_model=CoursePage)
def list_courses(
    db: DbSession,
    region: str | None = None,
    max_duration_minutes: Annotated[int | None, Query(ge=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> CoursePage:
    courses, total = repository.list_courses(
        db, region=region, max_duration_minutes=max_duration_minutes, page=page, size=size
    )
    return CoursePage(items=[course_response(course) for course in courses], meta=PageMeta(page=page, size=size, total=total))


@router.get("/{course_id}", response_model=CourseDetail)
def get_course(course_id: int, db: DbSession) -> CourseDetail:
    course = repository.get_course(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    waypoints = repository.course_waypoints(db, course_id)
    cafes = repository.course_cafes(db, course_id)
    return CourseDetail(
        **course_response(course).model_dump(),
        waypoints=[CourseWaypointResponse.model_validate(waypoint) for waypoint in waypoints],
        cafes=[
            CourseCafeResponse(
                id=cafe.id,
                name=cafe.name,
                address=cafe.address,
                latitude=cafe.latitude,
                longitude=cafe.longitude,
                recommendation_weight=weight,
            )
            for cafe, weight in cafes
        ],
    )
