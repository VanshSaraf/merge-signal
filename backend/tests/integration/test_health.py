from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.integrations.github.client import GitHubRestClient


def test_health_endpoint_returns_structured_status(monkeypatch) -> None:
    monkeypatch.setenv("MERGE_SIGNAL_ENVIRONMENT", "development")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "MergeSignal"
    assert body["environment"] == "development"
    assert "timestamp" in body
    get_settings.cache_clear()


def test_health_endpoint_does_not_construct_github_client(monkeypatch) -> None:
    def fail_if_constructed(*_args, **_kwargs) -> None:
        raise AssertionError("health endpoint must not use GitHub")

    monkeypatch.setattr(GitHubRestClient, "__init__", fail_if_constructed)
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200


def test_unhandled_errors_are_sanitized() -> None:
    app = create_app()

    @app.get("/_test/unhandled")
    def unhandled_error() -> None:
        raise RuntimeError("secret-token /Users/example/project Authorization: Bearer abc")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/_test/unhandled")

    assert response.status_code == 500
    body = response.json()
    serialized = response.text
    assert body == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "The request could not be completed.",
        }
    }
    assert "secret-token" not in serialized
    assert "Authorization" not in serialized
    assert "/Users/example" not in serialized
