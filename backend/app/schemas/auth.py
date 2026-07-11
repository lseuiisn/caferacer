from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import OAuthProvider, UserStatus


class SocialLoginRequest(BaseModel):
    provider: OAuthProvider
    provider_credential: str = Field(min_length=10)
    device_name: str | None = Field(default=None, max_length=100)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class IdentityResponse(BaseModel):
    provider: OAuthProvider
    linked_at: datetime


class MeResponse(BaseModel):
    id: int
    nickname: str | None
    status: UserStatus
    identities: list[IdentityResponse]
