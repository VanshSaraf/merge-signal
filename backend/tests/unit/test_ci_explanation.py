from datetime import UTC, datetime, timedelta

import pytest

from app.domain.pull_request import (
    CheckRunRecord,
    CiSurfaceCategory,
    CiSurfaceType,
    CommitStatusRecord,
)
from app.services.ci_explanation import build_ci_explanation, ci_provider_display_name
from app.services.ci_state import aggregate_ci_state


BASE_TIME = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)


def check_run(
    name: str,
    *,
    conclusion: str | None = "success",
    status: str = "completed",
    provider: str = "GitHub Actions",
    details_url: str | None = "https://github.com/octocat/Hello-World/actions/runs/1/job/2",
    id: int = 1,
) -> CheckRunRecord:
    return CheckRunRecord(
        id=id,
        name=name,
        status=status,
        conclusion=conclusion,
        provider_name=provider,
        provider_slug="github-actions",
        details_url=details_url,
        started_at=BASE_TIME,
        completed_at=BASE_TIME + timedelta(minutes=1),
    )


def commit_status(
    context: str,
    *,
    state: str = "success",
    description: str | None = None,
    target_url: str | None = None,
    creator_login: str | None = None,
    id: int = 1,
) -> CommitStatusRecord:
    return CommitStatusRecord(
        id=id,
        context=context,
        state=state,
        description=description,
        target_url=target_url,
        creator_login=creator_login,
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )


def explain(checks: list[CheckRunRecord], statuses: list[CommitStatusRecord]):
    ci = aggregate_ci_state(
        checks,
        statuses,
        check_runs_complete=True,
        commit_statuses_complete=True,
        check_run_pages_fetched=1,
        commit_status_pages_fetched=1,
        total_check_runs=len(checks),
    )
    return build_ci_explanation(ci)


def test_ci_explanation_identifies_blocking_vercel_authorization_status() -> None:
    explanation = explain(
        [
            check_run("End-to-end tests", id=10),
            check_run("Static checks & unit tests", id=11),
        ],
        [
            commit_status(
                "Vercel",
                state="failure",
                description="Authorization required to deploy.",
                target_url="https://vercel.com/git/authorize?repo=octocat",
                creator_login="vercel[bot]",
            )
        ],
    )

    assert explanation.overall_state == "failing"
    assert explanation.passing_count == 2
    assert explanation.failing_count == 1
    assert explanation.blocking_items[0].provider == "Vercel"
    assert explanation.blocking_items[0].category == CiSurfaceCategory.AUTHORIZATION_OR_CONFIGURATION
    assert explanation.blocking_items[0].details_url == "https://vercel.com/git/authorize?repo=octocat"
    assert "1 authorization/configuration check is failing on Vercel" in explanation.summary
    assert "2 checks passed" in explanation.summary


def test_ci_explanation_groups_surfaces_and_filters_unsafe_urls() -> None:
    explanation = explain(
        [
            check_run("Build", details_url="javascript:alert(1)", id=1),
            check_run("Build", details_url="javascript:alert(1)", id=2),
            check_run("Lint", conclusion="failure", details_url="https://github.com/octocat/Hello-World/actions/runs/1", id=3),
        ],
        [
            commit_status("deploy preview", state="pending", target_url="https://example.com/status", creator_login="DeployBot"),
        ],
    )

    assert explanation.total_count == 3
    assert explanation.blocking_items[0].name == "Lint"
    assert explanation.blocking_items[0].details_url == "https://github.com/octocat/Hello-World/actions/runs/1"
    assert explanation.surfaces[0].source_type == CiSurfaceType.COMMIT_STATUS
    build_item = next(item for surface in explanation.surfaces for item in surface.items if item.name == "Build")
    assert build_item.details_url is None
    assert build_item.category == CiSurfaceCategory.BUILD


@pytest.mark.parametrize(
    ("name", "provider", "description", "expected"),
    [
        ("Unit tests", "GitHub Actions", None, CiSurfaceCategory.TEST),
        ("Lint", "GitHub Actions", None, CiSurfaceCategory.LINT),
        ("Type check", "GitHub Actions", None, CiSurfaceCategory.TYPECHECK),
        ("Build", "GitHub Actions", None, CiSurfaceCategory.BUILD),
        ("Deploy preview", "Vercel", None, CiSurfaceCategory.DEPLOYMENT),
        ("Security scan", "GitHub Actions", None, CiSurfaceCategory.SECURITY),
        ("Coverage quality gate", "Sonar", None, CiSurfaceCategory.QUALITY),
        ("Vercel", "Vercel", "Authorization required to deploy.", CiSurfaceCategory.AUTHORIZATION_OR_CONFIGURATION),
        ("Custom", "Internal", None, CiSurfaceCategory.UNKNOWN),
    ],
)
def test_ci_categories_are_deterministic(name: str, provider: str, description: str | None, expected: CiSurfaceCategory) -> None:
    if description:
        explanation = explain([], [commit_status(name, state="failure", description=description, creator_login=provider)])
    else:
        explanation = explain([check_run(name, provider=provider)], [])

    item = explanation.blocking_items[0] if explanation.blocking_items else explanation.surfaces[0].items[0]
    assert item.category == expected


@pytest.mark.parametrize(
    ("raw_label", "expected"),
    [
        ("github", "GitHub"),
        ("gitHub", "GitHub"),
        ("GITHUB", "GitHub"),
        ("Github", "GitHub"),
        ("github actions", "GitHub Actions"),
        ("GITHUB_ACTIONS", "GitHub Actions"),
        ("Github Actions", "GitHub Actions"),
        ("github checks", "GitHub Checks"),
        ("GITHUB-CHECKS", "GitHub Checks"),
        ("internal ci", "Internal CI"),
    ],
)
def test_provider_display_names_normalize_known_github_sources_and_keep_unknowns_readable(raw_label: str, expected: str) -> None:
    assert ci_provider_display_name(raw_label) == expected


def test_all_passing_summary_and_check_run_only_input() -> None:
    explanation = explain([check_run("Unit tests"), check_run("Build", id=2)], [])

    assert explanation.overall_state == "passing"
    assert explanation.summary == "All 2 visible CI checks passed."
    assert explanation.surfaces[0].source_type == CiSurfaceType.CHECK_RUN
    assert not explanation.blocking_items


def test_commit_status_only_failure_remains_traceable() -> None:
    explanation = explain(
        [],
        [commit_status("build", state="failure", target_url="https://ci.example.com/build/1")],
    )

    assert explanation.overall_state == "failing"
    assert explanation.blocking_items[0].source_type == CiSurfaceType.COMMIT_STATUS
    assert explanation.blocking_items[0].category == CiSurfaceCategory.BUILD
    assert explanation.blocking_items[0].details_url == "https://ci.example.com/build/1"


def test_pending_neutral_skipped_and_missing_states_are_explained() -> None:
    pending = explain([check_run("Deploy", conclusion=None, status="queued")], [])
    mixed = explain([check_run("Optional", conclusion="neutral"), check_run("Skipped docs", conclusion="skipped", id=2)], [])
    missing = explain([], [])

    assert pending.summary == "1 check is still pending."
    assert pending.pending_count == 1
    assert mixed.neutral_count == 1
    assert mixed.skipped_count == 1
    assert mixed.unknown_count == 0
    assert missing.summary == "No CI checks were visible for the current head SHA."
    assert missing.total_count == 0


def test_stable_ordering_prioritizes_blockers_then_pending_then_passing() -> None:
    explanation = explain(
        [
            check_run("Build", conclusion="success", provider="Zeta", id=1),
            check_run("Unit tests", conclusion="failure", provider="GitHub Actions", id=2),
            check_run("Deploy", conclusion=None, status="queued", provider="DeployBot", id=3),
        ],
        [],
    )

    providers = [surface.provider for surface in explanation.surfaces]
    assert explanation.blocking_items[0].name == "Unit tests"
    assert providers == ["DeployBot", "GitHub Actions", "Zeta"]
