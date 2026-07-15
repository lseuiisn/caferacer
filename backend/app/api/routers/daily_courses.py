from datetime import date

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select

from app.api.deps import AdminUser, DbSession
from app.api.routers.courses import course_response
from app.models.catalog import Course
from app.models.social import DailyCourseRecommendation
from app.repositories.catalog import CatalogRepository
from app.schemas.daily_courses import (
    DailyCourseItem,
    DailyCourseResponse,
    DailyCourseSet,
)

router = APIRouter(prefix="/daily-courses", tags=["daily-courses"])
admin_router = APIRouter(prefix="/admin/daily-courses", tags=["admin-daily-courses"])
catalog = CatalogRepository()


@router.get("", response_model=DailyCourseResponse)
def get_daily_courses(db: DbSession, recommendation_date: date | None = None) -> DailyCourseResponse:
    target_date = recommendation_date or date.today()
    rows = list(
        db.execute(
            select(DailyCourseRecommendation, Course)
            .join(Course, Course.id == DailyCourseRecommendation.course_id)
            .where(
                DailyCourseRecommendation.recommendation_date == target_date,
                Course.is_active.is_(True),
            )
            .order_by(DailyCourseRecommendation.display_order)
        )
    )
    ids = [course.id for _, course in rows]
    counts = catalog.course_cafe_counts(db, ids)
    moods = catalog.course_moods(db, ids)
    return DailyCourseResponse(
        recommendation_date=target_date,
        items=[
            DailyCourseItem(
                display_order=item.display_order,
                headline=item.headline,
                course=course_response(
                    course,
                    cafe_count=counts.get(course.id, 0),
                    moods=moods.get(course.id, []),
                ),
            )
            for item, course in rows
        ],
    )


@admin_router.put("", response_model=DailyCourseResponse)
def set_daily_courses(payload: DailyCourseSet, _: AdminUser, db: DbSession) -> DailyCourseResponse:
    course_ids = [item.course_id for item in payload.items]
    found_ids = set(db.scalars(select(Course.id).where(Course.id.in_(course_ids), Course.is_active.is_(True))))
    if found_ids != set(course_ids):
        raise HTTPException(status_code=422, detail="One or more active courses do not exist")
    db.execute(
        delete(DailyCourseRecommendation).where(
            DailyCourseRecommendation.recommendation_date == payload.recommendation_date
        )
    )
    db.add_all(
        [
            DailyCourseRecommendation(
                recommendation_date=payload.recommendation_date,
                course_id=item.course_id,
                display_order=item.display_order,
                headline=item.headline,
            )
            for item in payload.items
        ]
    )
    db.commit()
    return get_daily_courses(db, payload.recommendation_date)
