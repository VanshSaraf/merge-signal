from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_github_client
from app.domain.pull_request import (
    ChangedFile,
    GitHubRateLimit,
    PullRequestAuthor,
    PullRequestBranch,
    PullRequestCommit,
    PullRequestMetadata,
    PullRequestReference,
    PullRequestSnapshot,
    SnapshotCompleteness,
)
from app.errors import (
    GitHubAccessDeniedError,
    GitHubAuthenticationFailedError,
    GitHubInvalidResponseError,
    GitHubPaginationLimitExceededError,
    GitHubPullRequestNotFoundError,
    GitHubRateLimitedError,
    GitHubUnavailableError,
    INVALID_PULL_REQUEST_URL,
)
from app.main import create_app


def make_snapshot(reference: PullRequestReference) -> PullRequestSnapshot:
    return PullRequestSnapshot(
        reference=reference,
        metadata=PullRequestMetadata(
            number=reference.pull_number,
            title="Improve merge signal collection",
            body=None,
            state="open",
            draft=False,
            html_url=reference.canonical_url,
            author=PullRequestAuthor(
                login="octocat",
                avatar_url="https://avatars.githubusercontent.com/u/1?v=4",
                html_url="https://github.com/octocat",
            ),
            base_branch=PullRequestBranch(
                ref="main",
                sha="base-sha",
                repository_full_name="octocat/Hello-World",
            ),
            head_branch=PullRequestBranch(
                ref="feature/signal",
                sha="head-sha",
                repository_full_name="octocat/Hello-World",
            ),
            head_sha="head-sha",
            created_at=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 7, 2, 10, 0, tzinfo=UTC),
            closed_at=None,
            merged_at=None,
            additions=12,
            deletions=4,
            changed_files=2,
            commit_count=2,
            mergeable=None,
            mergeable_state=None,
            labels=["backend"],
        ),
        files=[
            ChangedFile(
                filename="backend/app/main.py",
                status="modified",
                additions=5,
                deletions=1,
                changes=6,
                patch="@@ -1 +1 @@",
                previous_filename=None,
                blob_url="https://github.com/octocat/Hello-World/blob/head/backend/app/main.py",
            ),
            ChangedFile(
                filename="docs/old.md",
                status="renamed",
                additions=1,
                deletions=1,
                changes=2,
                patch=None,
                previous_filename="docs/legacy.md",
                blob_url=None,
            ),
        ],
        commits=[
            PullRequestCommit(
                sha="commit-one",
                message="Add metadata client",
                html_url="https://github.com/octocat/Hello-World/commit/commit-one",
                author_login="octocat",
                author_name="Octo Cat",
                authored_at=datetime(2026, 7, 1, 11, 0, tzinfo=UTC),
                committed_at=datetime(2026, 7, 1, 11, 5, tzinfo=UTC),
            ),
            PullRequestCommit(
                sha="commit-two",
                message="Handle files",
                html_url=None,
                author_login=None,
                author_name="Safe Fixture",
                authored_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
                committed_at=datetime(2026, 7, 1, 12, 5, tzinfo=UTC),
            ),
        ],
        completeness=SnapshotCompleteness(
            files_complete=True,
            commits_complete=True,
            missing_patch_count=1,
            warnings=["One or more changed files do not include patch data from GitHub."],
        ),
        fetched_at=datetime(2026, 7, 3, 10, 0, tzinfo=UTC),
        rate_limit=GitHubRateLimit(
            limit=5000,
            remaining=4998,
            used=2,
            resource="core",
            reset_at=datetime(2026, 7, 3, 11, 0, tzinfo=UTC),
        ),
    )


class FakeGitHubClient:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.references: list[PullRequestReference] = []

    async def get_pull_request_snapshot(
        self,
        reference: PullRequestReference,
    ) -> PullRequestSnapshot:
        self.references.append(reference)
        if self.error:
            raise self.error
        return make_snapshot(reference)


def client_with_fake(fake: FakeGitHubClient) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_github_client] = lambda: fake
    return TestClient(app)


def test_snapshot_endpoint_returns_exact_shape_and_normalizes_url() -> None:
    fake = FakeGitHubClient()
    client = client_with_fake(fake)

    response = client.post(
        "/api/v1/pull-requests/snapshot",
        json={"url": "https://github.com/octocat/Hello-World/pull/42?tab=files#discussion"},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data"}
    data = body["data"]
    assert data["reference"] == {
        "owner": "octocat",
        "repository": "Hello-World",
        "pull_number": 42,
        "canonical_url": "https://github.com/octocat/Hello-World/pull/42",
    }
    assert data["metadata"]["title"] == "Improve merge signal collection"
    assert data["files"][1]["patch"] is None
    assert data["files"][1]["previous_filename"] == "docs/legacy.md"
    assert [commit["sha"] for commit in data["commits"]] == ["commit-one", "commit-two"]
    assert data["completeness"]["missing_patch_count"] == 1
    assert data["rate_limit"]["remaining"] == 4998
    assert fake.references[0].canonical_url == "https://github.com/octocat/Hello-World/pull/42"


def test_snapshot_endpoint_reuses_invalid_url_contract() -> None:
    response = client_with_fake(FakeGitHubClient()).post(
        "/api/v1/pull-requests/snapshot",
        json={"url": "https://github.com/octocat/Hello-World/issues/42"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == INVALID_PULL_REQUEST_URL


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (GitHubPullRequestNotFoundError(), 404, "GITHUB_PULL_REQUEST_NOT_FOUND"),
        (GitHubRateLimitedError(metadata={"reset_at": "2026-07-03T11:00:00+00:00"}), 429, "GITHUB_RATE_LIMITED"),
        (GitHubAccessDeniedError(), 403, "GITHUB_ACCESS_DENIED"),
        (GitHubAuthenticationFailedError(), 502, "GITHUB_AUTHENTICATION_FAILED"),
        (GitHubUnavailableError(), 503, "GITHUB_UNAVAILABLE"),
        (GitHubInvalidResponseError(), 502, "GITHUB_INVALID_RESPONSE"),
        (GitHubPaginationLimitExceededError(), 502, "GITHUB_PAGINATION_LIMIT_EXCEEDED"),
    ],
)
def test_snapshot_endpoint_maps_github_errors(
    error: Exception,
    status_code: int,
    code: str,
) -> None:
    response = client_with_fake(FakeGitHubClient(error)).post(
        "/api/v1/pull-requests/snapshot",
        json={"url": "https://github.com/octocat/Hello-World/pull/42"},
    )

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


def test_snapshot_endpoint_request_validation_errors_remain_distinguishable() -> None:
    response = client_with_fake(FakeGitHubClient()).post(
        "/api/v1/pull-requests/snapshot",
        json={"url": "https://github.com/octocat/Hello-World/pull/42", "extra": True},
    )

    assert response.status_code == 422
    assert "detail" in response.json()
    assert "error" not in response.json()


def test_snapshot_endpoint_rejects_malformed_json() -> None:
    response = client_with_fake(FakeGitHubClient()).post(
        "/api/v1/pull-requests/snapshot",
        content='{"url":',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_existing_parse_and_health_endpoints_still_work() -> None:
    client = client_with_fake(FakeGitHubClient())

    assert client.get("/health").status_code == 200
    parse_response = client.post(
        "/api/v1/pull-requests/parse",
        json={"url": "https://github.com/octocat/Hello-World/pull/42"},
    )

    assert parse_response.status_code == 200


def test_openapi_contains_snapshot_endpoint_and_models() -> None:
    response = client_with_fake(FakeGitHubClient()).get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    operation = document["paths"]["/api/v1/pull-requests/snapshot"]["post"]
    schemas = document["components"]["schemas"]

    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/FetchPullRequestSnapshotRequest"
    )
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/FetchPullRequestSnapshotResponse"
    )
    for status_code in ["403", "404", "429", "502", "503"]:
        assert operation["responses"][status_code]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("/ApiErrorResponse")
    assert "PullRequestSnapshot" in schemas
    assert "FetchPullRequestSnapshotRequest" in schemas
    assert "FetchPullRequestSnapshotResponse" in schemas
