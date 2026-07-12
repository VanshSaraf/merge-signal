import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.domain.pull_request import PullRequestReference
from app.errors import (
    GitHubAccessDeniedError,
    GitHubAuthenticationFailedError,
    GitHubInvalidResponseError,
    GitHubPaginationLimitExceededError,
    GitHubPullRequestNotFoundError,
    GitHubRateLimitedError,
    GitHubRequestFailedError,
    GitHubUnavailableError,
)
from app.integrations.github.client import GitHubRestClient, extract_rate_limit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "github"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def reference() -> PullRequestReference:
    return PullRequestReference(
        owner="octocat",
        repository="Hello-World",
        pull_number=42,
        canonical_url="https://github.com/octocat/Hello-World/pull/42",
    )


async def noop_sleep(_seconds: float) -> None:
    return None


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def json_response(
    status_code: int,
    payload: Any,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return httpx.Response(status_code, json=payload, headers=headers or {})


def make_client(
    handler: httpx.MockTransport,
    settings: Settings | None = None,
) -> GitHubRestClient:
    resolved_settings = settings or Settings()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": resolved_settings.github_user_agent,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = resolved_settings.github_token_value
    if token:
        headers["Authorization"] = f"Bearer {token}"
    http_client = httpx.AsyncClient(
        transport=handler,
        base_url=resolved_settings.github_api_base_url_string,
        headers=headers,
    )
    return GitHubRestClient(resolved_settings, http_client=http_client, sleep=noop_sleep)


def test_request_construction_without_token() -> None:
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return json_response(200, load_fixture("pull_request.json"))

    client = make_client(httpx.MockTransport(handler))
    metadata = run(client.get_pull_request(reference()))

    assert metadata.number == 42
    assert seen_request is not None
    assert seen_request.url.path == "/repos/octocat/Hello-World/pulls/42"
    assert seen_request.headers["Accept"] == "application/vnd.github+json"
    assert seen_request.headers["User-Agent"] == "MergeSignal"
    assert seen_request.headers["X-GitHub-Api-Version"] == "2022-11-28"
    assert "Authorization" not in seen_request.headers
    run(client.aclose())


def test_request_construction_with_token_does_not_expose_token_in_errors() -> None:
    seen_request: httpx.Request | None = None
    settings = Settings(GITHUB_TOKEN="example-token")

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return json_response(401, {"message": "bad credentials"})

    client = make_client(httpx.MockTransport(handler), settings)

    with pytest.raises(GitHubAuthenticationFailedError) as exc_info:
        run(client.get_pull_request(reference()))

    assert seen_request is not None
    assert seen_request.headers["Authorization"] == "Bearer example-token"
    assert "example-token" not in repr(exc_info.value)
    run(client.aclose())


def test_get_pull_request_normalizes_metadata() -> None:
    client = make_client(httpx.MockTransport(lambda _request: json_response(200, load_fixture("pull_request.json"))))

    metadata = run(client.get_pull_request(reference()))

    assert metadata.title == "Improve merge signal collection"
    assert metadata.body is None
    assert metadata.mergeable is None
    assert metadata.labels == ["backend", "safe-fixture"]
    assert metadata.base_branch.repository_full_name == "octocat/Hello-World"
    assert metadata.created_at.tzinfo is not None
    run(client.aclose())


def test_get_pull_request_rejects_invalid_json_and_schema() -> None:
    invalid_json_client = make_client(
        httpx.MockTransport(lambda _request: httpx.Response(200, content=b"{"))
    )
    with pytest.raises(GitHubInvalidResponseError):
        run(invalid_json_client.get_pull_request(reference()))

    invalid_schema_client = make_client(httpx.MockTransport(lambda _request: json_response(200, {})))
    with pytest.raises(GitHubInvalidResponseError):
        run(invalid_schema_client.get_pull_request(reference()))

    run(invalid_json_client.aclose())
    run(invalid_schema_client.aclose())


def test_list_pull_request_files_paginates_and_preserves_order() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.params.get("page") == "1":
            return json_response(
                200,
                load_fixture("pull_request_files_page_1.json"),
                {
                    "Link": '<https://api.github.com/repos/octocat/Hello-World/pulls/42/files?page=2>; rel="next"',
                },
            )
        return json_response(200, load_fixture("pull_request_files_page_2.json"))

    client = make_client(httpx.MockTransport(handler), Settings(GITHUB_PER_PAGE=2))
    files = run(client.list_pull_request_files(reference()))

    assert [file.filename for file in files] == ["backend/app/main.py", "docs/old.md", "README.md"]
    assert files[1].previous_filename == "docs/legacy.md"
    assert files[1].patch is None
    assert len(requests) == 2
    run(client.aclose())


def test_list_pull_request_files_handles_empty_page() -> None:
    client = make_client(httpx.MockTransport(lambda _request: json_response(200, [])))

    assert run(client.list_pull_request_files(reference())) == []
    run(client.aclose())


def test_list_pull_request_commits_paginates_and_preserves_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("page") == "1":
            return json_response(
                200,
                load_fixture("pull_request_commits_page_1.json"),
                {
                    "Link": '<https://api.github.com/repos/octocat/Hello-World/pulls/42/commits?page=2>; rel="next"',
                },
            )
        return json_response(200, load_fixture("pull_request_commits_page_2.json"))

    client = make_client(httpx.MockTransport(handler), Settings(GITHUB_PER_PAGE=2))
    commits = run(client.list_pull_request_commits(reference()))

    assert [commit.sha for commit in commits] == ["commit-one", "commit-two", "commit-three"]
    assert commits[0].author_login == "octocat"
    assert commits[1].author_login is None
    assert commits[0].authored_at is not None
    run(client.aclose())


def test_snapshot_completeness_and_latest_rate_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        headers = {
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4997",
            "X-RateLimit-Used": "3",
            "X-RateLimit-Resource": "core",
            "X-RateLimit-Reset": "1780000000",
        }
        path = request.url.path
        if path.endswith("/files"):
            return json_response(200, load_fixture("pull_request_files_page_1.json") + load_fixture("pull_request_files_page_2.json"), headers)
        if path.endswith("/commits"):
            return json_response(200, load_fixture("pull_request_commits_page_1.json"), headers)
        return json_response(200, load_fixture("pull_request.json"), headers)

    client = make_client(httpx.MockTransport(handler))
    snapshot = run(client.get_pull_request_snapshot(reference()))

    assert snapshot.completeness.files_complete is True
    assert snapshot.completeness.commits_complete is False
    assert snapshot.completeness.missing_patch_count == 1
    assert snapshot.completeness.warnings
    assert snapshot.rate_limit.remaining == 4997
    assert snapshot.rate_limit.reset_at is not None
    run(client.aclose())


def test_extract_rate_limit_handles_absent_and_malformed_values() -> None:
    rate_limit = extract_rate_limit(httpx.Headers({"X-RateLimit-Limit": "bad", "X-RateLimit-Reset": "bad"}))

    assert rate_limit.limit is None
    assert rate_limit.remaining is None
    assert rate_limit.reset_at is None


@pytest.mark.parametrize(
    ("status_code", "error_type", "headers"),
    [
        (401, GitHubAuthenticationFailedError, {}),
        (403, GitHubAccessDeniedError, {}),
        (403, GitHubRateLimitedError, {"X-RateLimit-Remaining": "0"}),
        (404, GitHubPullRequestNotFoundError, {}),
        (429, GitHubRateLimitedError, {}),
        (500, GitHubRequestFailedError, {}),
    ],
)
def test_error_mapping(status_code: int, error_type: type[Exception], headers: dict[str, str]) -> None:
    client = make_client(httpx.MockTransport(lambda _request: json_response(status_code, {"message": "nope"}, headers)))

    with pytest.raises(error_type):
        run(client.get_pull_request(reference()))

    run(client.aclose())


@pytest.mark.parametrize("status_code", [502, 503, 504])
def test_transient_status_retries_then_succeeds(status_code: int) -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return json_response(status_code, {"message": "temporary"})
        return json_response(200, load_fixture("pull_request.json"))

    client = make_client(httpx.MockTransport(handler), Settings(GITHUB_MAX_RETRIES=1))

    assert run(client.get_pull_request(reference())).number == 42
    assert attempts == 2
    run(client.aclose())


@pytest.mark.parametrize("error", [httpx.ConnectError("offline"), httpx.ReadTimeout("slow")])
def test_transport_errors_retry_then_succeed(error: Exception) -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise error
        return json_response(200, load_fixture("pull_request.json"))

    client = make_client(httpx.MockTransport(handler), Settings(GITHUB_MAX_RETRIES=1))

    assert run(client.get_pull_request(reference())).number == 42
    assert attempts == 2
    run(client.aclose())


def test_retry_exhaustion_maps_to_unavailable() -> None:
    client = make_client(
        httpx.MockTransport(lambda _request: json_response(503, {"message": "temporary"})),
        Settings(GITHUB_MAX_RETRIES=1),
    )

    with pytest.raises(GitHubUnavailableError):
        run(client.get_pull_request(reference()))

    run(client.aclose())


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 429])
def test_non_retry_statuses_are_not_retried(status_code: int) -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return json_response(status_code, {"message": "no retry"})

    client = make_client(httpx.MockTransport(handler), Settings(GITHUB_MAX_RETRIES=2))

    with pytest.raises(Exception):
        run(client.get_pull_request(reference()))

    assert attempts == 1
    run(client.aclose())


def test_unsafe_and_repeated_pagination_raise_stable_error() -> None:
    unsafe_client = make_client(
        httpx.MockTransport(
            lambda _request: json_response(
                200,
                load_fixture("pull_request_files_page_1.json"),
                {"Link": '<https://evil.example/page=2>; rel="next"'},
            )
        )
    )
    with pytest.raises(GitHubPaginationLimitExceededError):
        run(unsafe_client.list_pull_request_files(reference()))

    repeated_client = make_client(
        httpx.MockTransport(
            lambda _request: json_response(
                200,
                load_fixture("pull_request_files_page_1.json"),
                {"Link": '<https://api.github.com/repos/octocat/Hello-World/pulls/42/files?page=1>; rel="next"'},
            )
        )
    )
    with pytest.raises(GitHubPaginationLimitExceededError):
        run(repeated_client.list_pull_request_files(reference()))

    run(unsafe_client.aclose())
    run(repeated_client.aclose())


def test_max_page_limit_raises_stable_error() -> None:
    client = make_client(
        httpx.MockTransport(
            lambda _request: json_response(
                200,
                load_fixture("pull_request_files_page_1.json"),
                {"Link": '<https://api.github.com/repos/octocat/Hello-World/pulls/42/files?page=2>; rel="next"'},
            )
        ),
        Settings(GITHUB_MAX_PAGES=1),
    )

    with pytest.raises(GitHubPaginationLimitExceededError):
        run(client.list_pull_request_files(reference()))

    run(client.aclose())
