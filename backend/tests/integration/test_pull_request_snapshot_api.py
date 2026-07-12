from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_github_client
from app.domain.pull_request import (
    ChangedFile,
    CheckRunRecord,
    CiCompleteness,
    CiState,
    CiVisibility,
    CommitStatusRecord,
    GitHubRateLimit,
    PullRequestCi,
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
from app.services.file_classifier import classify_changed_files
from app.signals.engine import analyze_snapshot_signals


def make_snapshot(reference: PullRequestReference) -> PullRequestSnapshot:
    files = [
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
    ]
    classified_files, classification_summary = classify_changed_files(files)
    snapshot = PullRequestSnapshot(
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
        files=classified_files,
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
        ci=PullRequestCi(
            state=CiState.PASSING,
            visibility=CiVisibility.COMPLETE,
            check_runs=[
                CheckRunRecord(
                    id=101,
                    name="unit tests",
                    status="completed",
                    conclusion="success",
                    provider_name="GitHub Actions",
                    provider_slug="github-actions",
                    details_url="https://ci.example.test/unit",
                    started_at=datetime(2026, 7, 3, 10, 0, tzinfo=UTC),
                    completed_at=datetime(2026, 7, 3, 10, 3, tzinfo=UTC),
                )
            ],
            commit_statuses=[
                CommitStatusRecord(
                    id=201,
                    context="build",
                    state="success",
                    description="Build passed",
                    target_url="https://ci.example.test/build/2",
                    creator_login="ci-bot",
                    created_at=datetime(2026, 7, 3, 10, 20, tzinfo=UTC),
                    updated_at=datetime(2026, 7, 3, 10, 21, tzinfo=UTC),
                )
            ],
            total_check_runs=1,
            total_status_contexts=1,
            passing_count=2,
            failing_count=0,
            pending_count=0,
            neutral_count=0,
            skipped_count=0,
            warnings=[],
            fetched_at=datetime(2026, 7, 3, 10, 30, tzinfo=UTC),
            completeness=CiCompleteness(
                check_runs_complete=True,
                commit_statuses_complete=True,
                check_run_pages_fetched=1,
                commit_status_pages_fetched=1,
                raw_status_record_count=1,
                unique_status_context_count=1,
                warnings=[],
            ),
            rate_limit=GitHubRateLimit(
                limit=5000,
                remaining=4997,
                used=3,
                resource="core",
                reset_at=datetime(2026, 7, 3, 11, 0, tzinfo=UTC),
            ),
        ),
        classification_summary=classification_summary,
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
    signal_result = analyze_snapshot_signals(snapshot)
    return snapshot.model_copy(update={"signals": signal_result.signals, "signal_summary": signal_result.summary})


class FakeGitHubClient:
    def __init__(
        self,
        error: Exception | None = None,
        snapshot: PullRequestSnapshot | None = None,
    ) -> None:
        self.error = error
        self.snapshot = snapshot
        self.references: list[PullRequestReference] = []

    async def get_pull_request_snapshot(
        self,
        reference: PullRequestReference,
    ) -> PullRequestSnapshot:
        self.references.append(reference)
        if self.error:
            raise self.error
        if self.snapshot:
            return self.snapshot
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
    assert data["files"][0]["classification"]["primary_kind"] == "source"
    assert data["files"][0]["classification"]["language"] == "python"
    assert data["files"][0]["classification"]["areas"] == ["backend"]
    assert data["files"][1]["classification"]["primary_kind"] == "documentation"
    assert data["files"][1]["classification"]["language"] == "markdown"
    assert data["files"][1]["previous_classification"]["primary_kind"] == "documentation"
    assert data["classification_summary"]["total_files"] == 2
    assert data["classification_summary"]["renamed_files"] == 1
    assert data["classification_summary"]["files_with_previous_classification"] == 1
    assert data["classification_summary"]["files_without_patch"] == 1
    assert {"name": "source", "count": 1} in data["classification_summary"]["counts_by_kind"]
    assert {"name": "documentation", "count": 1} in data["classification_summary"]["counts_by_kind"]
    assert "signals" in data
    assert "signal_summary" in data
    signal_ids = [signal["rule_id"] for signal in data["signals"]]
    assert "metadata.missing_description" in signal_ids
    assert "testing.production_change_without_test_files" in signal_ids
    assert "completeness.patch_coverage_incomplete" in signal_ids
    first_signal = data["signals"][0]
    assert set(first_signal) == {
        "id",
        "rule_id",
        "title",
        "description",
        "category",
        "severity",
        "scope",
        "affected_files",
        "evidence",
        "limitations",
        "tags",
    }
    assert data["signal_summary"]["total_signals"] == len(data["signals"])
    assert data["signal_summary"]["rules_version"] == "v1"
    assert "backend/app/main.py" in data["signal_summary"]["files_with_signals"]
    assert [commit["sha"] for commit in data["commits"]] == ["commit-one", "commit-two"]
    assert data["ci"]["state"] == "passing"
    assert data["ci"]["visibility"] == "complete"
    assert data["ci"]["check_runs"][0]["provider_slug"] == "github-actions"
    assert data["ci"]["commit_statuses"][0]["context"] == "build"
    assert "risk_score" not in data
    assert "evidence_confidence" not in data
    assert "merge_decision" not in data
    assert "blockers" not in data
    assert "recommendations" not in data
    assert "ranked_files" not in data
    assert data["completeness"]["missing_patch_count"] == 1
    assert data["rate_limit"]["remaining"] == 4998
    assert fake.references[0].canonical_url == "https://github.com/octocat/Hello-World/pull/42"


@pytest.mark.parametrize(
    ("state", "visibility"),
    [
        (CiState.FAILING, CiVisibility.COMPLETE),
        (CiState.PENDING, CiVisibility.COMPLETE),
        (CiState.MISSING, CiVisibility.COMPLETE),
        (CiState.UNKNOWN, CiVisibility.UNAVAILABLE),
        (CiState.FAILING, CiVisibility.PARTIAL),
    ],
)
def test_snapshot_endpoint_serializes_ci_state_and_visibility(
    state: CiState,
    visibility: CiVisibility,
) -> None:
    base = make_snapshot(
        PullRequestReference(
            owner="octocat",
            repository="Hello-World",
            pull_number=42,
            canonical_url="https://github.com/octocat/Hello-World/pull/42",
        )
    )
    snapshot = base.model_copy(
        update={
            "ci": base.ci.model_copy(
                update={
                    "state": state,
                    "visibility": visibility,
                    "warnings": ["CI visibility warning."] if visibility != CiVisibility.COMPLETE else [],
                }
            )
        }
    )

    response = client_with_fake(FakeGitHubClient(snapshot=snapshot)).post(
        "/api/v1/pull-requests/snapshot",
        json={"url": "https://github.com/octocat/Hello-World/pull/42"},
    )

    assert response.status_code == 200
    ci = response.json()["data"]["ci"]
    assert ci["state"] == state
    assert ci["visibility"] == visibility
    if visibility != CiVisibility.COMPLETE:
        assert ci["warnings"]


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
    assert "PullRequestCi" in schemas
    assert "CiState" in schemas
    assert "CiVisibility" in schemas
    assert "FileClassification" in schemas
    assert "FileClassificationSummary" in schemas
    assert "FileKind" in schemas
    assert "FileArea" in schemas
    assert "FileLanguage" in schemas
    assert "ReviewSignal" in schemas
    assert "SignalEvidence" in schemas
    assert "ReviewSignalSummary" in schemas
    assert "SignalSeverity" in schemas
    assert "SignalCategory" in schemas
    assert "SignalScope" in schemas
    assert "EvidenceKind" in schemas
    assert "FetchPullRequestSnapshotRequest" in schemas
    assert "FetchPullRequestSnapshotResponse" in schemas
