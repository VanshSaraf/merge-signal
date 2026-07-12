import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_github_settings_defaults_and_empty_token() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.cors_origin_list == ["http://127.0.0.1:5173", "http://localhost:5173"]
    assert settings.github_api_base_url_string == "https://api.github.com"
    assert settings.github_token_value is None
    assert settings.github_request_timeout_seconds == 10
    assert settings.github_max_retries == 2
    assert settings.github_retry_base_delay_seconds == 0.25
    assert settings.github_per_page == 100
    assert settings.github_max_pages == 30
    assert settings.github_user_agent == "MergeSignal"


def test_github_token_is_secret() -> None:
    settings = Settings(GITHUB_TOKEN="example-token", _env_file=None)

    assert settings.github_token_value == "example-token"
    assert "example-token" not in repr(settings)
    assert "example-token" not in str(settings.github_token)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"GITHUB_REQUEST_TIMEOUT_SECONDS": 0},
        {"GITHUB_MAX_RETRIES": -1},
        {"GITHUB_PER_PAGE": 0},
        {"GITHUB_PER_PAGE": 101},
        {"GITHUB_MAX_PAGES": 0},
        {"GITHUB_API_BASE_URL": "not a url"},
    ],
)
def test_github_settings_validation(kwargs: dict) -> None:
    with pytest.raises(ValidationError):
        Settings(**kwargs)


def test_cors_origins_support_multiple_values_and_normalize_trailing_slashes() -> None:
    settings = Settings(
        cors_origins=" https://app.example.com/ , https://preview.example.com ",
    )

    assert settings.cors_origin_list == ["https://app.example.com", "https://preview.example.com"]


@pytest.mark.parametrize(
    "cors_origins",
    [
        "not-a-url",
        "ftp://app.example.com",
        "https://user:password@app.example.com",
        "https://app.example.com/path",
        "https://app.example.com?debug=true",
    ],
)
def test_cors_origins_reject_malformed_values(cors_origins: str) -> None:
    with pytest.raises(ValidationError):
        Settings(cors_origins=cors_origins)


def test_production_allows_explicit_frontend_origin_allowlist() -> None:
    settings = Settings(environment="production", cors_origins="https://app.example.com")

    assert settings.is_production is True
    assert settings.cors_origin_list == ["https://app.example.com"]


@pytest.mark.parametrize("cors_origins", ["", "*"])
def test_production_cors_never_uses_wildcard_or_empty_allowlist(cors_origins: str) -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", cors_origins=cors_origins)
