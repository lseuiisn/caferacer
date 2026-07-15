from datetime import datetime

from typing import Literal

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
    description: str | None
    estimated_duration_minutes: int
    estimated_distance_meters: int
    difficulty: str
    recommended_season: str
    recommended_time: str
    thumbnail_url: str | None
    cafe_count: int = 0
    moods: list[str] = []


class CoursePathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sequence: int
    latitude: float
    longitude: float
    road_name: str | None
    road_type: str


class CoursePolyline(BaseModel):
    type: Literal["polyline"] = "polyline"
    coordinates: list[tuple[float, float]]


class CourseCafeResponse(BaseModel):
    id: int
    name: str
    address: str
    latitude: float
    longitude: float
    stop_order: int
    tags: list[str] = []


class CourseNavigationAnchorResponse(BaseModel):
    sequence: int
    name: str
    anchor_type: str
    latitude: float
    longitude: float
    pass_radius_meters: int


class CourseDetail(CourseListItem):
    path: CoursePolyline
    path_points: list[CoursePathResponse] = []
    cafes: list[CourseCafeResponse] = []
    navigation_anchors: list[CourseNavigationAnchorResponse] = []


class CoursePage(BaseModel):
    items: list[CourseListItem]
    meta: PageMeta
