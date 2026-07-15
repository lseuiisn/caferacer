from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.catalog import CourseCafeResponse, CourseListItem


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RecommendationFilters(BaseModel):
    parking_required: bool = False
    price_ranges: list[str] = []
    tags: list[str] = []


class RecommendationRequest(BaseModel):
    origin: Coordinate
    round_trip_minutes: int = Field(ge=30, le=1440)
    moods: list[str] = []
    filters: RecommendationFilters = RecommendationFilters()
    season: str | None = None
    difficulty: str | None = None


class RecommendationItem(BaseModel):
    course: CourseListItem
    cafes: list[CourseCafeResponse]
    estimated_round_trip_minutes: int
    estimated_distance_meters: int
    score: int = Field(ge=0, le=100)
    reason: list[str]


class RecommendationResponse(BaseModel):
    items: list[RecommendationItem]


class CourseNavigationRequest(BaseModel):
    origin: Coordinate


class NavigationAnchorResponse(BaseModel):
    sequence: int
    name: str
    anchor_type: str
    latitude: float
    longitude: float
    pass_radius_meters: int


class CourseNavigationResponse(BaseModel):
    distance_meters: int
    duration_seconds: int
    start_point: Coordinate
    provider: Literal["tmap"] = "tmap"
    requires_background_location: bool = True
    anchors: list[NavigationAnchorResponse]
