from fastapi.testclient import TestClient

from app.errors import INVALID_PULL_REQUEST_URL, INVALID_PULL_REQUEST_URL_MESSAGE
from app.main import create_app


def test_parse_pull_request_url_returns_exact_success_shape() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/pull-requests/parse",
        json={"url": "https://github.com/octocat/Hello-World/pull/1347"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "data": {
            "owner": "octocat",
            "repository": "Hello-World",
            "pull_number": 1347,
            "canonical_url": "https://github.com/octocat/Hello-World/pull/1347",
        }
    }


def test_parse_pull_request_url_normalizes_query_fragment_and_trailing_slash() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/pull-requests/parse",
        json={"url": "https://github.com/Owner/Repo/pull/99/?tab=files#discussion"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "owner": "Owner",
        "repository": "Repo",
        "pull_number": 99,
        "canonical_url": "https://github.com/Owner/Repo/pull/99",
    }


def test_parse_pull_request_url_returns_stable_invalid_url_error() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/pull-requests/parse",
        json={"url": "https://github.com/octocat/Hello-World/issues/1347"},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "error": {
            "code": INVALID_PULL_REQUEST_URL,
            "message": INVALID_PULL_REQUEST_URL_MESSAGE,
        }
    }


def test_parse_pull_request_url_rejects_unsupported_host() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/pull-requests/parse",
        json={"url": "https://gitlab.com/octocat/Hello-World/pull/1347"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == INVALID_PULL_REQUEST_URL


def test_parse_pull_request_url_rejects_empty_and_whitespace_urls() -> None:
    client = TestClient(create_app())

    for value in ["", " https://github.com/octocat/Hello-World/pull/1347"]:
        response = client.post("/api/v1/pull-requests/parse", json={"url": value})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == INVALID_PULL_REQUEST_URL


def test_parse_pull_request_url_rejects_unknown_request_fields() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/pull-requests/parse",
        json={"url": "https://github.com/octocat/Hello-World/pull/1347", "extra": True},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_parse_pull_request_url_request_validation_errors_are_distinguishable() -> None:
    client = TestClient(create_app())

    invalid_payloads = [
        {},
        {"url": None},
        {"url": 123},
        {"url": True},
        {"url": ["https://github.com/octocat/Hello-World/pull/1347"]},
        {"url": {"value": "https://github.com/octocat/Hello-World/pull/1347"}},
    ]

    for payload in invalid_payloads:
        response = client.post("/api/v1/pull-requests/parse", json=payload)

        assert response.status_code == 422
        assert "detail" in response.json()
        assert "error" not in response.json()


def test_parse_pull_request_url_rejects_malformed_json() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/pull-requests/parse",
        content='{"url":',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_openapi_contains_parse_endpoint_and_schemas() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    operation = document["paths"]["/api/v1/pull-requests/parse"]["post"]
    schemas = document["components"]["schemas"]

    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ParsePullRequestUrlRequest"
    )
    assert (
        operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
            "/ParsePullRequestUrlResponse"
        )
    )
    assert (
        operation["responses"]["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
            "/ApiErrorResponse"
        )
    )
    assert "PullRequestReference" in schemas
    assert "ParsePullRequestUrlRequest" in schemas
    assert "ParsePullRequestUrlResponse" in schemas
    assert "ApiErrorResponse" in schemas
