from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str
    jwt_secret_key: str = Field(min_length=32)
    jwt_access_token_minutes: int = Field(default=30, gt=0)
    jwt_refresh_token_days: int = Field(default=30, gt=0)
    google_client_ids: str = ""
    kakao_rest_api_key: str = ""
    tmap_app_key: str = ""
    cors_origins: str = ""

    @property
    def google_client_id_list(self) -> list[str]:
        return [client_id.strip() for client_id in self.google_client_ids.split(",") if client_id.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
