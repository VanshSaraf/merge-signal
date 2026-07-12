from functools import lru_cache

from pydantic import AliasChoices, AnyUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="local")
    project_name: str = Field(default="MergeSignal")
    cors_origins: str = Field(default="http://127.0.0.1:5173,http://localhost:5173")
    github_api_base_url: AnyUrl = Field(
        default="https://api.github.com",
        validation_alias=AliasChoices("GITHUB_API_BASE_URL", "MERGE_SIGNAL_GITHUB_API_BASE_URL"),
    )
    github_token: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("GITHUB_TOKEN", "MERGE_SIGNAL_GITHUB_TOKEN"),
    )
    github_request_timeout_seconds: float = Field(
        default=10,
        gt=0,
        validation_alias=AliasChoices(
            "GITHUB_REQUEST_TIMEOUT_SECONDS",
            "MERGE_SIGNAL_GITHUB_REQUEST_TIMEOUT_SECONDS",
        ),
    )
    github_max_retries: int = Field(
        default=2,
        ge=0,
        validation_alias=AliasChoices("GITHUB_MAX_RETRIES", "MERGE_SIGNAL_GITHUB_MAX_RETRIES"),
    )
    github_retry_base_delay_seconds: float = Field(
        default=0.25,
        ge=0,
        validation_alias=AliasChoices(
            "GITHUB_RETRY_BASE_DELAY_SECONDS",
            "MERGE_SIGNAL_GITHUB_RETRY_BASE_DELAY_SECONDS",
        ),
    )
    github_per_page: int = Field(
        default=100,
        ge=1,
        le=100,
        validation_alias=AliasChoices("GITHUB_PER_PAGE", "MERGE_SIGNAL_GITHUB_PER_PAGE"),
    )
    github_max_pages: int = Field(
        default=30,
        gt=0,
        validation_alias=AliasChoices("GITHUB_MAX_PAGES", "MERGE_SIGNAL_GITHUB_MAX_PAGES"),
    )
    github_user_agent: str = Field(
        default="MergeSignal",
        min_length=1,
        validation_alias=AliasChoices("GITHUB_USER_AGENT", "MERGE_SIGNAL_GITHUB_USER_AGENT"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MERGE_SIGNAL_",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def github_api_base_url_string(self) -> str:
        return str(self.github_api_base_url).rstrip("/")

    @property
    def github_token_value(self) -> str | None:
        value = self.github_token.get_secret_value().strip()
        return value or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
