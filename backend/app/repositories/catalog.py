from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.catalog import Cafe, CafeImage, CafeTag, CafeTagAssignment, Course, CourseCafe, CourseWaypoint


class CatalogRepository:
    def list_cafes(
        self,
        db: Session,
        *,
        tags: list[str] | None,
        parking: bool | None,
        price_ranges: list[str] | None,
        page: int,
        size: int,
    ) -> tuple[list[Cafe], int]:
        filters = [Cafe.is_active.is_(True)]
        if parking is not None:
            filters.append(Cafe.parking_available.is_(parking))
        if price_ranges:
            filters.append(Cafe.price_range.in_(price_ranges))

        base_query: Select[tuple[Cafe]] = select(Cafe).where(*filters)
        if tags:
            base_query = (
                base_query.join(CafeTagAssignment, CafeTagAssignment.cafe_id == Cafe.id)
                .join(CafeTag, CafeTag.id == CafeTagAssignment.tag_id)
                .where(CafeTag.code.in_(tags))
                .group_by(Cafe.id)
                .having(func.count(func.distinct(CafeTag.code)) == len(set(tags)))
            )
        total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0
        cafes = list(
            db.scalars(base_query.order_by(Cafe.verified_at.desc(), Cafe.id.desc()).offset((page - 1) * size).limit(size))
        )
        return cafes, total

    def get_cafe(self, db: Session, cafe_id: int) -> Cafe | None:
        return db.scalar(select(Cafe).where(Cafe.id == cafe_id, Cafe.is_active.is_(True)))

    def cafe_tags(self, db: Session, cafe_ids: list[int]) -> dict[int, list[str]]:
        if not cafe_ids:
            return {}
        rows = db.execute(
            select(CafeTagAssignment.cafe_id, CafeTag.code)
            .join(CafeTag, CafeTag.id == CafeTagAssignment.tag_id)
            .where(CafeTagAssignment.cafe_id.in_(cafe_ids))
            .order_by(CafeTag.category, CafeTag.display_name)
        )
        result: dict[int, list[str]] = {cafe_id: [] for cafe_id in cafe_ids}
        for cafe_id, tag_code in rows:
            result[cafe_id].append(tag_code)
        return result

    def cafe_images(self, db: Session, cafe_ids: list[int]) -> dict[int, list[CafeImage]]:
        if not cafe_ids:
            return {}
        rows = db.scalars(
            select(CafeImage)
            .where(CafeImage.cafe_id.in_(cafe_ids))
            .order_by(CafeImage.cafe_id, CafeImage.display_order, CafeImage.id)
        )
        result: dict[int, list[CafeImage]] = {cafe_id: [] for cafe_id in cafe_ids}
        for image in rows:
            result[image.cafe_id].append(image)
        return result

    def list_courses(
        self, db: Session, *, region: str | None, max_duration_minutes: int | None, page: int, size: int
    ) -> tuple[list[Course], int]:
        filters = [Course.is_active.is_(True)]
        if region:
            filters.append(Course.region == region)
        if max_duration_minutes:
            filters.append(Course.estimated_duration_minutes <= max_duration_minutes)
        base_query = select(Course).where(*filters)
        total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0
        courses = list(
            db.scalars(
                base_query.order_by(Course.drive_suitability_score.desc(), Course.id.desc())
                .offset((page - 1) * size)
                .limit(size)
            )
        )
        return courses, total

    def get_course(self, db: Session, course_id: int) -> Course | None:
        return db.scalar(select(Course).where(Course.id == course_id, Course.is_active.is_(True)))

    def course_waypoints(self, db: Session, course_id: int) -> list[CourseWaypoint]:
        return list(
            db.scalars(
                select(CourseWaypoint)
                .where(CourseWaypoint.course_id == course_id)
                .order_by(CourseWaypoint.sequence)
            )
        )

    def course_cafes(self, db: Session, course_id: int) -> list[tuple[Cafe, float]]:
        return list(
            db.execute(
                select(Cafe, CourseCafe.recommendation_weight)
                .join(CourseCafe, CourseCafe.cafe_id == Cafe.id)
                .where(CourseCafe.course_id == course_id, Cafe.is_active.is_(True))
                .order_by(CourseCafe.recommendation_weight.desc(), Cafe.name)
            )
        )
