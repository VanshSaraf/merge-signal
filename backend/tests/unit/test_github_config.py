import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_github_settings_defaults_and_empty_token() -> None:
    settings = Settings()

    assert settings.github_api_base_url_string == "https://api.github.com"
    assert settings.github_token_value is None
    assert settings.github_request_timeout_seconds == 10
    assert settings.github_max_retries == 2
    assert settings.github_retry_base_delay_seconds == 0.25
    assert settings.github_per_page == 100
    assert settings.github_max_pages == 30
    assert settings.github_user_agent == "MergeSignal"


def test_github_token_is_secret() -> None:
    settings = Settings(GITHUB_TOKEN="example-token")

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
