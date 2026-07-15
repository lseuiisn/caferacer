from pydantic import BaseModel, Field, model_validator

from app.models.enums import NavigationAnchorType


class CoursePathInput(BaseModel):
    sequence: int = Field(ge=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    road_name: str | None = Field(default=None, max_length=120)
    road_type: str = Field(default="unknown", max_length=30)


class NavigationAnchorInput(BaseModel):
    sequence: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=120)
    anchor_type: NavigationAnchorType
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    pass_radius_meters: int = Field(default=100, ge=30, le=1000)


class CourseUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    region: str = Field(min_length=1, max_length=30)
    estimated_duration_minutes: int = Field(gt=0, le=1440)
    estimated_distance_meters: int = Field(gt=0)
    difficulty: str = Field(default="normal", max_length=20)
    recommended_season: str = Field(default="all", max_length=20)
    recommended_time: str = Field(default="day", max_length=20)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    drive_suitability_score: float = Field(default=0, ge=0, le=10)
    moods: list[str] = []
    cafe_ids: list[int] = []
    path: list[CoursePathInput] = Field(min_length=2)
    navigation_anchors: list[NavigationAnchorInput] = Field(min_length=2, max_length=12)

    @model_validator(mode="after")
    def validate_route(self) -> "CourseUpsert":
        path_sequences = [item.sequence for item in self.path]
        anchor_sequences = [item.sequence for item in self.navigation_anchors]
        if path_sequences != sorted(path_sequences) or len(path_sequences) != len(set(path_sequences)):
            raise ValueError("path sequences must be unique and ascending")
        if anchor_sequences != sorted(anchor_sequences) or len(anchor_sequences) != len(set(anchor_sequences)):
            raise ValueError("anchor sequences must be unique and ascending")
        starts = [item for item in self.navigation_anchors if item.anchor_type == NavigationAnchorType.START]
        destinations = [item for item in self.navigation_anchors if item.anchor_type == NavigationAnchorType.DESTINATION]
        waypoints = [item for item in self.navigation_anchors if item.anchor_type == NavigationAnchorType.WAYPOINT]
        if len(starts) != 1 or len(destinations) != 1:
            raise ValueError("exactly one start and one destination anchor are required")
        if len(waypoints) > 10:
            raise ValueError("a course can have at most 10 waypoints")
        if len(self.cafe_ids) != len(set(self.cafe_ids)):
            raise ValueError("cafe_ids must be unique")
        return self


class CourseAdminResponse(BaseModel):
    id: int
    name: str
    path_point_count: int
    waypoint_count: int
    cafe_count: int
