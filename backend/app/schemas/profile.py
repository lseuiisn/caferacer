from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdate(BaseModel):
    nickname: str | None = Field(default=None, min_length=2, max_length=50)
    bio: str | None = Field(default=None, max_length=300)
    profile_image_url: str | None = Field(default=None, max_length=500)


class VehicleCreate(BaseModel):
    manufacturer: str | None = Field(default=None, max_length=80)
    model_name: str = Field(min_length=1, max_length=100)
    model_year: int | None = Field(default=None, ge=1900, le=2100)
    is_primary: bool = False


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    manufacturer: str | None
    model_name: str
    model_year: int | None
    is_primary: bool


class ProfileResponse(BaseModel):
    user_id: int
    nickname: str | None
    bio: str | None
    profile_image_url: str | None
    connected_accounts: list[str]
    vehicles: list[VehicleResponse]
    created_at: datetime
