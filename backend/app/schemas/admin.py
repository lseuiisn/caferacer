from pydantic import BaseModel, Field

from app.schemas.recommendations import Coordinate


class CafeImportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=500)


class CafeImportReview(BaseModel):
    address: str = Field(min_length=1, max_length=255)
    coordinate: Coordinate
    source_url: str = Field(min_length=1, max_length=500)
    parking_available: bool = False
    price_range: str | None = None


class CafeImportResponse(BaseModel):
    id: int
    name: str
    address: str | None
    search_url: str
    status: str
    cafe_id: int | None = None
