from collections.abc import Iterable
from datetime import UTC, datetime

from app.domain.pull_request import (
    CheckRunRecord,
    CiCompleteness,
    CiState,
    CiVisibility,
    CommitStatusRecord,
    GitHubRateLimit,
    PullRequestCi,
)

PASSING_CHECK_CONCLUSIONS = {"success"}
NEUTRAL_CHECK_CONCLUSIONS = {"neutral"}
SKIPPED_CHECK_CONCLUSIONS = {"skipped"}
FAILING_CHECK_CONCLUSIONS = {
    "failure",
    "timed_out",
    "cancelled",
    "action_required",
    "startup_failure",
    "stale",
}
PENDING_CHECK_STATUSES = {"queued", "in_progress", "waiting", "requested", "pending"}
PASSING_STATUS_STATES = {"success"}
FAILING_STATUS_STATES = {"failure", "error"}
PENDING_STATUS_STATES = {"pending"}


def current_statuses_by_context(statuses: Iterable[CommitStatusRecord]) -> list[CommitStatusRecord]:
    current: dict[str, CommitStatusRecord] = {}
    for status in statuses:
        if status.context not in current:
            current[status.context] = status
    return list(current.values())


def aggregate_ci_state(
    check_runs: list[CheckRunRecord],
    raw_statuses: list[CommitStatusRecord],
    *,
    check_runs_complete: bool,
    commit_statuses_complete: bool,
    check_run_pages_fetched: int,
    commit_status_pages_fetched: int,
    total_check_runs: int | None,
    warnings: list[str] | None = None,
    rate_limit: GitHubRateLimit | None = None,
) -> PullRequestCi:
    """Aggregate normalized CI records without making merge-readiness claims."""
    current_statuses = current_statuses_by_context(raw_statuses)
    warnings = list(warnings or [])

    classifications = [_classify_check_run(run, warnings) for run in check_runs]
    classifications.extend(_classify_status(status, warnings) for status in current_statuses)

    passing_count = classifications.count("passing")
    failing_count = classifications.count("failing")
    pending_count = classifications.count("pending")
    neutral_count = classifications.count("neutral")
    skipped_count = classifications.count("skipped")
    unknown_count = classifications.count("unknown")

    if not classifications:
        state = CiState.MISSING if check_runs_complete and commit_statuses_complete else CiState.UNKNOWN
    elif failing_count:
        state = CiState.FAILING
    elif pending_count:
        state = CiState.PENDING
    elif unknown_count:
        state = CiState.UNKNOWN
    elif passing_count and not (neutral_count or skipped_count) or passing_count:
        state = CiState.PASSING
    else:
        state = CiState.UNKNOWN

    if check_runs_complete and commit_statuses_complete:
        visibility = CiVisibility.COMPLETE
    elif not check_runs_complete and not commit_statuses_complete and not classifications:
        visibility = CiVisibility.UNAVAILABLE
    else:
        visibility = CiVisibility.PARTIAL

    completeness = CiCompleteness(
        check_runs_complete=check_runs_complete,
        commit_statuses_complete=commit_statuses_complete,
        check_run_pages_fetched=check_run_pages_fetched,
        commit_status_pages_fetched=commit_status_pages_fetched,
        raw_status_record_count=len(raw_statuses),
        unique_status_context_count=len(current_statuses),
        warnings=warnings,
    )

    return PullRequestCi(
        state=state,
        visibility=visibility,
        check_runs=check_runs,
        commit_statuses=current_statuses,
        total_check_runs=total_check_runs if total_check_runs is not None else len(check_runs),
        total_status_contexts=len(current_statuses),
        passing_count=passing_count,
        failing_count=failing_count,
        pending_count=pending_count,
        neutral_count=neutral_count,
        skipped_count=skipped_count,
        warnings=warnings,
        fetched_at=datetime.now(UTC),
        completeness=completeness,
        rate_limit=rate_limit,
    )


def _classify_check_run(run: CheckRunRecord, warnings: list[str]) -> str:
    status = run.status.lower()
    conclusion = run.conclusion.lower() if run.conclusion else None

    if status != "completed" or conclusion is None:
        if status in PENDING_CHECK_STATUSES:
            return "pending"
        warnings.append(f"Unsupported check-run status observed: {run.status}.")
        return "unknown"
    if conclusion in PASSING_CHECK_CONCLUSIONS:
        return "passing"
    if conclusion in NEUTRAL_CHECK_CONCLUSIONS:
        return "neutral"
    if conclusion in SKIPPED_CHECK_CONCLUSIONS:
        return "skipped"
    if conclusion in FAILING_CHECK_CONCLUSIONS:
        return "failing"

    warnings.append(f"Unsupported check-run conclusion observed: {run.conclusion}.")
    return "unknown"


def _classify_status(status_record: CommitStatusRecord, warnings: list[str]) -> str:
    state = status_record.state.lower()
    if state in PASSING_STATUS_STATES:
        return "passing"
    if state in FAILING_STATUS_STATES:
        return "failing"
    if state in PENDING_STATUS_STATES:
        return "pending"

    warnings.append(f"Unsupported commit-status state observed: {status_record.state}.")
    return "unknown"
