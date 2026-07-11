from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PageMeta(BaseModel):
    page: int
    size: int
    total: int


class CafeImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    alt_text: str | None
    display_order: int


class CafeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    latitude: float
    longitude: float
    price_range: str | None
    parking_available: bool
    tags: list[str] = []
    thumbnail_url: str | None = None


class CafeDetail(CafeListItem):
    phone_number: str | None
    business_hours: str | None
    verified_at: datetime | None
    images: list[CafeImageResponse] = []


class CafePage(BaseModel):
    items: list[CafeListItem]
    meta: PageMeta


class CourseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    region: str
    summary: str | None
    estimated_duration_minutes: int
    estimated_distance_meters: int
    drive_suitability_score: float


class CourseWaypointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sequence: int
    name: str
    latitude: float
    longitude: float
    waypoint_type: str


class CourseCafeResponse(BaseModel):
    id: int
    name: str
    address: str
    latitude: float
    longitude: float
    recommendation_weight: float


class CourseDetail(CourseListItem):
    waypoints: list[CourseWaypointResponse] = []
    cafes: list[CourseCafeResponse] = []


class CoursePage(BaseModel):
    items: list[CourseListItem]
    meta: PageMeta
