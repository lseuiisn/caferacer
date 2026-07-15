from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.catalog import (
    Cafe,
    CafeImage,
    CafeTag,
    CafeTagAssignment,
    Course,
    CourseCafe,
    CourseNavigationAnchor,
    CoursePath,
    CourseTag,
    CourseTagAssignment,
)


class CatalogRepository:
    def list_cafes(self, db: Session, *, tags: list[str] | None, parking: bool | None, price_ranges: list[str] | None, page: int, size: int) -> tuple[list[Cafe], int]:
        filters = [Cafe.is_active.is_(True)]
        if parking is not None:
            filters.append(Cafe.parking_available.is_(parking))
        if price_ranges:
            filters.append(Cafe.price_range.in_(price_ranges))
        base_query: Select[tuple[Cafe]] = select(Cafe).where(*filters)
        if tags:
            base_query = (base_query.join(CafeTagAssignment, CafeTagAssignment.cafe_id == Cafe.id).join(CafeTag, CafeTag.id == CafeTagAssignment.tag_id).where(CafeTag.code.in_(tags)).group_by(Cafe.id).having(func.count(func.distinct(CafeTag.code)) == len(set(tags))))
        total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0
        return list(db.scalars(base_query.order_by(Cafe.verified_at.desc(), Cafe.id.desc()).offset((page - 1) * size).limit(size))), total

    def get_cafe(self, db: Session, cafe_id: int) -> Cafe | None:
        return db.scalar(select(Cafe).where(Cafe.id == cafe_id, Cafe.is_active.is_(True)))

    def cafe_tags(self, db: Session, cafe_ids: list[int]) -> dict[int, list[str]]:
        result: dict[int, list[str]] = {cafe_id: [] for cafe_id in cafe_ids}
        if not cafe_ids:
            return result
        rows = db.execute(select(CafeTagAssignment.cafe_id, CafeTag.code).join(CafeTag, CafeTag.id == CafeTagAssignment.tag_id).where(CafeTagAssignment.cafe_id.in_(cafe_ids)).order_by(CafeTag.category, CafeTag.display_name))
        for cafe_id, code in rows:
            result[cafe_id].append(code)
        return result

    def cafe_images(self, db: Session, cafe_ids: list[int]) -> dict[int, list[CafeImage]]:
        result: dict[int, list[CafeImage]] = {cafe_id: [] for cafe_id in cafe_ids}
        if not cafe_ids:
            return result
        for image in db.scalars(select(CafeImage).where(CafeImage.cafe_id.in_(cafe_ids)).order_by(CafeImage.cafe_id, CafeImage.display_order, CafeImage.id)):
            result[image.cafe_id].append(image)
        return result

    def list_courses(self, db: Session, *, region: str | None, duration_minutes: int | None, moods: list[str] | None, season: str | None, difficulty: str | None, page: int, size: int) -> tuple[list[Course], int]:
        filters = [Course.is_active.is_(True)]
        if region:
            filters.append(Course.region.like(f"{region}%"))
        if duration_minutes:
            filters.append(Course.estimated_duration_minutes <= duration_minutes)
        if season:
            filters.append(Course.recommended_season.in_([season, "all"]))
        if difficulty:
            filters.append(Course.difficulty == difficulty)
        query: Select[tuple[Course]] = select(Course).where(*filters)
        if moods:
            query = (query.join(CourseTagAssignment, CourseTagAssignment.course_id == Course.id).join(CourseTag, CourseTag.id == CourseTagAssignment.tag_id).where(CourseTag.category == "mood", CourseTag.code.in_(moods)).group_by(Course.id).having(func.count(func.distinct(CourseTag.code)) == len(set(moods))))
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        courses = list(db.scalars(query.order_by(Course.drive_suitability_score.desc(), Course.id.desc()).offset((page - 1) * size).limit(size)))
        return courses, total

    def get_course(self, db: Session, course_id: int) -> Course | None:
        return db.scalar(select(Course).where(Course.id == course_id, Course.is_active.is_(True)))

    def course_paths(self, db: Session, course_id: int) -> list[CoursePath]:
        return list(db.scalars(select(CoursePath).where(CoursePath.course_id == course_id).order_by(CoursePath.sequence)))

    def course_start_point(self, db: Session, course_id: int) -> CoursePath | None:
        return db.scalar(select(CoursePath).where(CoursePath.course_id == course_id).order_by(CoursePath.sequence).limit(1))

    def course_navigation_anchors(
        self, db: Session, course_id: int
    ) -> list[CourseNavigationAnchor]:
        return list(
            db.scalars(
                select(CourseNavigationAnchor)
                .where(CourseNavigationAnchor.course_id == course_id)
                .order_by(CourseNavigationAnchor.sequence)
            )
        )

    def course_cafes(self, db: Session, course_id: int, *, parking_required: bool = False, price_ranges: list[str] | None = None, tags: list[str] | None = None) -> list[tuple[Cafe, int]]:
        query = select(Cafe, CourseCafe.stop_order).join(CourseCafe, CourseCafe.cafe_id == Cafe.id).where(CourseCafe.course_id == course_id, Cafe.is_active.is_(True))
        if parking_required:
            query = query.where(Cafe.parking_available.is_(True))
        if price_ranges:
            query = query.where(Cafe.price_range.in_(price_ranges))
        if tags:
            query = (query.join(CafeTagAssignment, CafeTagAssignment.cafe_id == Cafe.id).join(CafeTag, CafeTag.id == CafeTagAssignment.tag_id).where(CafeTag.code.in_(tags)).group_by(Cafe.id, CourseCafe.stop_order).having(func.count(func.distinct(CafeTag.code)) == len(set(tags))))
        return list(db.execute(query.order_by(CourseCafe.stop_order, Cafe.name)))

    def course_cafe_counts(self, db: Session, course_ids: list[int]) -> dict[int, int]:
        if not course_ids:
            return {}
        rows = db.execute(select(CourseCafe.course_id, func.count()).where(CourseCafe.course_id.in_(course_ids)).group_by(CourseCafe.course_id))
        return dict(rows.all())

    def course_moods(self, db: Session, course_ids: list[int]) -> dict[int, list[str]]:
        result: dict[int, list[str]] = {course_id: [] for course_id in course_ids}
        if not course_ids:
            return result
        rows = db.execute(select(CourseTagAssignment.course_id, CourseTag.code).join(CourseTag, CourseTag.id == CourseTagAssignment.tag_id).where(CourseTagAssignment.course_id.in_(course_ids), CourseTag.category == "mood").order_by(CourseTag.code))
        for course_id, code in rows:
            result[course_id].append(code)
        return result
