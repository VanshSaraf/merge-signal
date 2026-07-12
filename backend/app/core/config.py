from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="local")
    project_name: str = Field(default="MergeSignal")
    cors_origins: str = Field(default="http://127.0.0.1:5173,http://localhost:5173")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MERGE_SIGNAL_",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
