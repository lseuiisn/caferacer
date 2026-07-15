from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select

from app.api.deps import AdminUser, DbSession
from app.models.catalog import (
    Cafe,
    Course,
    CourseCafe,
    CourseNavigationAnchor,
    CoursePath,
    CourseTag,
    CourseTagAssignment,
)
from app.schemas.course_admin import CourseAdminResponse, CourseUpsert

router = APIRouter(prefix="/admin/courses", tags=["admin-courses"])


def save_course(db: DbSession, course: Course, payload: CourseUpsert) -> CourseAdminResponse:
    tags = list(db.scalars(select(CourseTag).where(CourseTag.code.in_(payload.moods))))
    if len(tags) != len(set(payload.moods)):
        raise HTTPException(status_code=422, detail="One or more course mood tags do not exist")
    cafes = list(db.scalars(select(Cafe).where(Cafe.id.in_(payload.cafe_ids))))
    if len(cafes) != len(payload.cafe_ids):
        raise HTTPException(status_code=422, detail="One or more cafes do not exist")

    course.name = payload.name
    course.description = payload.description
    course.region = payload.region
    course.estimated_duration_minutes = payload.estimated_duration_minutes
    course.estimated_distance_meters = payload.estimated_distance_meters
    course.difficulty = payload.difficulty
    course.recommended_season = payload.recommended_season
    course.recommended_time = payload.recommended_time
    course.thumbnail_url = payload.thumbnail_url
    course.drive_suitability_score = payload.drive_suitability_score
    course.is_active = True
    db.add(course)
    db.flush()

    for model in [CoursePath, CourseNavigationAnchor, CourseCafe, CourseTagAssignment]:
        db.execute(delete(model).where(model.course_id == course.id))
    db.add_all(
        [
            CoursePath(course_id=course.id, **item.model_dump())
            for item in payload.path
        ]
    )
    db.add_all(
        [
            CourseNavigationAnchor(course_id=course.id, **item.model_dump())
            for item in payload.navigation_anchors
        ]
    )
    db.add_all(
        [
            CourseCafe(
                course_id=course.id,
                cafe_id=cafe_id,
                stop_order=stop_order,
                recommendation_weight=1,
            )
            for stop_order, cafe_id in enumerate(payload.cafe_ids, start=1)
        ]
    )
    db.add_all(
        [CourseTagAssignment(course_id=course.id, tag_id=tag.id) for tag in tags]
    )
    db.commit()
    return CourseAdminResponse(
        id=course.id,
        name=course.name,
        path_point_count=len(payload.path),
        waypoint_count=sum(
            item.anchor_type.value == "waypoint" for item in payload.navigation_anchors
        ),
        cafe_count=len(payload.cafe_ids),
    )


@router.post("", response_model=CourseAdminResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseUpsert,
    _: AdminUser,
    db: DbSession,
) -> CourseAdminResponse:
    if db.scalar(select(Course.id).where(Course.name == payload.name)):
        raise HTTPException(status_code=409, detail="Course name already exists")
    return save_course(
        db,
        Course(
            name=payload.name,
            region=payload.region,
            estimated_duration_minutes=payload.estimated_duration_minutes,
            estimated_distance_meters=payload.estimated_distance_meters,
        ),
        payload,
    )


@router.put("/{course_id}", response_model=CourseAdminResponse)
def update_course(
    course_id: int,
    payload: CourseUpsert,
    _: AdminUser,
    db: DbSession,
) -> CourseAdminResponse:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return save_course(db, course, payload)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_course(course_id: int, _: AdminUser, db: DbSession) -> None:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    course.is_active = False
    db.commit()
