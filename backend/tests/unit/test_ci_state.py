from datetime import UTC, datetime, timedelta

import pytest

from app.domain.pull_request import (
    CheckRunRecord,
    CiState,
    CiVisibility,
    CommitStatusRecord,
)
from app.services.ci_state import aggregate_ci_state


BASE_TIME = datetime(2026, 7, 3, 10, 0, tzinfo=UTC)


def check_run(
    conclusion: str | None = "success",
    status: str = "completed",
    name: str = "check",
) -> CheckRunRecord:
    return CheckRunRecord(
        id=1,
        name=name,
        status=status,
        conclusion=conclusion,
        provider_name="CI",
        provider_slug="ci",
        details_url=None,
        started_at=BASE_TIME,
        completed_at=BASE_TIME + timedelta(minutes=1) if status == "completed" else None,
    )


def commit_status(
    state: str = "success",
    context: str = "build",
    created_at: datetime = BASE_TIME,
    id: int = 1,
) -> CommitStatusRecord:
    return CommitStatusRecord(
        id=id,
        context=context,
        state=state,
        description=None,
        target_url=None,
        creator_login=None,
        created_at=created_at,
        updated_at=created_at,
    )


def aggregate(
    checks: list[CheckRunRecord] | None = None,
    statuses: list[CommitStatusRecord] | None = None,
    check_runs_complete: bool = True,
    commit_statuses_complete: bool = True,
):
    return aggregate_ci_state(
        checks or [],
        statuses or [],
        check_runs_complete=check_runs_complete,
        commit_statuses_complete=commit_statuses_complete,
        check_run_pages_fetched=1 if check_runs_complete else 0,
        commit_status_pages_fetched=1 if commit_statuses_complete else 0,
        total_check_runs=len(checks or []),
    )


@pytest.mark.parametrize(
    "records",
    [
        ([check_run("success")], []),
        ([], [commit_status("success")]),
        ([check_run("success")], [commit_status("success")]),
    ],
)
def test_ci_aggregate_passing(records: tuple[list[CheckRunRecord], list[CommitStatusRecord]]) -> None:
    ci = aggregate(*records)

    assert ci.state == CiState.PASSING
    assert ci.visibility == CiVisibility.COMPLETE
    assert ci.passing_count >= 1


@pytest.mark.parametrize(
    ("checks", "statuses"),
    [
        ([check_run("failure")], []),
        ([check_run("cancelled")], []),
        ([check_run("timed_out")], []),
        ([check_run("action_required")], []),
        ([check_run("startup_failure")], []),
        ([check_run("stale")], []),
        ([], [commit_status("failure")]),
        ([], [commit_status("error")]),
        ([check_run(None, "in_progress")], [commit_status("failure")]),
    ],
)
def test_ci_aggregate_failing_precedence(
    checks: list[CheckRunRecord],
    statuses: list[CommitStatusRecord],
) -> None:
    ci = aggregate(checks, statuses)

    assert ci.state == CiState.FAILING
    assert ci.failing_count >= 1


@pytest.mark.parametrize(
    ("checks", "statuses"),
    [
        ([check_run(None, "queued")], []),
        ([check_run(None, "in_progress")], []),
        ([], [commit_status("pending")]),
        ([check_run("success")], [commit_status("pending")]),
    ],
)
def test_ci_aggregate_pending_without_failure(
    checks: list[CheckRunRecord],
    statuses: list[CommitStatusRecord],
) -> None:
    assert aggregate(checks, statuses).state == CiState.PENDING


@pytest.mark.parametrize("checks", [[check_run("neutral")], [check_run("skipped")]])
def test_all_neutral_or_skipped_is_unknown(checks: list[CheckRunRecord]) -> None:
    assert aggregate(checks, []).state == CiState.UNKNOWN


def test_passing_plus_neutral_or_skipped_is_passing() -> None:
    assert aggregate([check_run("success"), check_run("neutral")], []).state == CiState.PASSING
    assert aggregate([check_run("success"), check_run("skipped")], []).state == CiState.PASSING


def test_unknown_plus_success_is_unknown() -> None:
    ci = aggregate([check_run("future_conclusion"), check_run("success")], [])

    assert ci.state == CiState.UNKNOWN
    assert ci.warnings


def test_unknown_incomplete_check_status_is_unknown() -> None:
    ci = aggregate([check_run(None, "future_status")], [])

    assert ci.state == CiState.UNKNOWN
    assert ci.warnings == ["Unsupported check-run status observed: future_status."]


def test_no_records_after_successful_retrieval_is_missing() -> None:
    ci = aggregate([], [])

    assert ci.state == CiState.MISSING
    assert ci.visibility == CiVisibility.COMPLETE


def test_no_records_after_failed_ci_sources_is_unavailable() -> None:
    ci = aggregate([], [], check_runs_complete=False, commit_statuses_complete=False)

    assert ci.state == CiState.UNKNOWN
    assert ci.visibility == CiVisibility.UNAVAILABLE


def test_partial_visibility_independent_from_failing_state() -> None:
    ci = aggregate([check_run("failure")], [], commit_statuses_complete=False)

    assert ci.state == CiState.FAILING
    assert ci.visibility == CiVisibility.PARTIAL


def test_repeated_status_context_uses_latest_record_only() -> None:
    older_failed = commit_status("failure", context="build", created_at=BASE_TIME, id=1)
    newer_success = commit_status(
        "success",
        context="build",
        created_at=BASE_TIME + timedelta(minutes=2),
        id=2,
    )

    ci = aggregate([], [newer_success, older_failed])

    assert ci.state == CiState.PASSING
    assert ci.total_status_contexts == 1
    assert ci.completeness.raw_status_record_count == 2
    assert ci.completeness.unique_status_context_count == 1
    assert ci.commit_statuses[0].id == 2


def test_older_success_followed_by_newer_failure_is_current_failure() -> None:
    newer_failed = commit_status(
        "failure",
        context="build",
        created_at=BASE_TIME + timedelta(minutes=2),
        id=2,
    )

    ci = aggregate([], [newer_failed, commit_status("success", context="build", id=1)])

    assert ci.state == CiState.FAILING
    assert ci.failing_count == 1
    assert ci.passing_count == 0
