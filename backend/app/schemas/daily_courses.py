from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.schemas.catalog import CourseListItem


class DailyCourseAssignment(BaseModel):
    course_id: int = Field(gt=0)
    display_order: int = Field(ge=1, le=3)
    headline: str | None = Field(default=None, max_length=120)


class DailyCourseSet(BaseModel):
    recommendation_date: date
    items: list[DailyCourseAssignment] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def validate_unique(self) -> "DailyCourseSet":
        course_ids = [item.course_id for item in self.items]
        orders = [item.display_order for item in self.items]
        if len(course_ids) != len(set(course_ids)) or len(orders) != len(set(orders)):
            raise ValueError("course ids and display orders must be unique")
        return self


class DailyCourseItem(BaseModel):
    display_order: int
    headline: str | None
    course: CourseListItem


class DailyCourseResponse(BaseModel):
    recommendation_date: date
    items: list[DailyCourseItem]
