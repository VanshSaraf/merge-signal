from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.file_priority import FilePriorityLevel, RankedFile
from app.domain.pull_request import (
    ChangedFile,
    CiCompleteness,
    CiState,
    CiVisibility,
    GitHubRateLimit,
    PullRequestAuthor,
    PullRequestBranch,
    PullRequestCi,
    PullRequestCommit,
    PullRequestMetadata,
    PullRequestReference,
    PullRequestSnapshot,
    SnapshotCompleteness,
    CheckRunRecord,
    CommitStatusRecord,
    PullRequestReviewRecord,
    ReviewCommentRecord,
    ReviewState,
)
from app.domain.review_action import (
    ReviewAction,
    ReviewActionCategory,
    ReviewActionCount,
    ReviewActionPriority,
    ReviewActionSummary,
)
from app.domain.review_signal import EvidenceKind, ReviewSignal, SignalCategory, SignalEvidence, SignalScope, SignalSeverity
from app.domain.scoring import ConfidenceComponentStatus
from app.file_priority import calculate_file_priorities
from app.readiness import calculate_merge_readiness
from app.review_actions import build_review_actions
from app.review_actions.rules import REVIEW_ACTION_RULES_VERSION, RULES
from app.scoring import calculate_evidence_confidence, calculate_merge_risk
from app.services.ci_explanation import build_ci_explanation
from app.services.ci_state import aggregate_ci_state
from app.services.file_classifier import classify_changed_files
from app.services.review_context import build_review_context, sanitize_review_body
from app.signals.engine import analyze_snapshot_signals

BASE_TIME = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)


def changed_file(
    filename: str,
    *,
    status: str = "modified",
    additions: int = 1,
    deletions: int = 1,
    changes: int | None = None,
    patch: str | None = "@@ -1 +1 @@\n-old\n+new",
    previous_filename: str | None = None,
) -> ChangedFile:
    return ChangedFile(
        filename=filename,
        status=status,
        additions=additions,
        deletions=deletions,
        changes=changes if changes is not None else additions + deletions,
        patch=patch,
        previous_filename=previous_filename,
        blob_url=None,
    )


def manual_signal(
    rule_id: str,
    *,
    signal_id: str | None = None,
    affected_files: list[str] | None = None,
    category: SignalCategory = SignalCategory.CHANGE_SCOPE,
    scope: SignalScope = SignalScope.FILE_SET,
    severity: SignalSeverity = SignalSeverity.MEDIUM,
) -> ReviewSignal:
    return ReviewSignal(
        id=signal_id or f"{rule_id}:fixture",
        rule_id=rule_id,
        title=f"Observed {rule_id}",
        description="Fixture signal.",
        category=category,
        severity=severity,
        scope=scope,
        affected_files=affected_files or [],
        evidence=[SignalEvidence(kind=EvidenceKind.METADATA, message="Fixture evidence.")],
        limitations=[],
        tags=["fixture"],
    )


def review_comment(
    id: int,
    reviewer_login: str,
    body: str,
    *,
    created_at: datetime = BASE_TIME,
    in_reply_to_id: int | None = None,
    path: str = "backend/app/main.py",
) -> ReviewCommentRecord:
    return ReviewCommentRecord(
        id=id,
        reviewer_login=reviewer_login,
        body_excerpt=sanitize_review_body(body) or "",
        created_at=created_at,
        updated_at=None,
        html_url=f"https://github.com/octocat/Hello-World/pull/42#discussion_r{id}",
        pull_request_review_id=900,
        in_reply_to_id=in_reply_to_id,
        path=path,
        line=12,
        start_line=None,
        side="RIGHT",
        start_side=None,
        current_position=3,
        original_position=3,
        commit_sha="head",
    )


def review_record(
    id: int,
    reviewer_login: str,
    state: ReviewState,
    *,
    submitted_at: datetime = BASE_TIME,
    commit_sha: str = "head",
) -> PullRequestReviewRecord:
    return PullRequestReviewRecord(
        id=id,
        reviewer_login=reviewer_login,
        state=state,
        submitted_at=submitted_at,
        body_excerpt=None,
        html_url=f"https://github.com/octocat/Hello-World/pull/42#pullrequestreview-{id}",
        commit_sha=commit_sha,
    )


def base_snapshot(
    files: list[ChangedFile],
    *,
    signals: list[ReviewSignal] | None = None,
    ci_state: CiState = CiState.PASSING,
    ci_visibility: CiVisibility = CiVisibility.COMPLETE,
    check_runs: list[CheckRunRecord] | None = None,
    commit_statuses: list[CommitStatusRecord] | None = None,
    review_context=None,
    files_complete: bool = True,
    commits_complete: bool = True,
) -> PullRequestSnapshot:
    classified_files, classification_summary = classify_changed_files(files)
    ci = (
        aggregate_ci_state(
            check_runs or [],
            commit_statuses or [],
            check_runs_complete=True,
            commit_statuses_complete=True,
            check_run_pages_fetched=1,
            commit_status_pages_fetched=1,
            total_check_runs=len(check_runs or []),
        )
        if check_runs is not None or commit_statuses is not None
        else PullRequestCi(
            state=ci_state,
            visibility=ci_visibility,
            check_runs=[],
            commit_statuses=[],
            total_check_runs=0,
            total_status_contexts=0,
            passing_count=1 if ci_state == CiState.PASSING else 0,
            failing_count=1 if ci_state == CiState.FAILING else 0,
            pending_count=1 if ci_state == CiState.PENDING else 0,
            neutral_count=0,
            skipped_count=0,
            warnings=[],
            fetched_at=BASE_TIME,
            completeness=CiCompleteness(
                check_runs_complete=ci_visibility != CiVisibility.UNAVAILABLE,
                commit_statuses_complete=ci_visibility == CiVisibility.COMPLETE,
                check_run_pages_fetched=1,
                commit_status_pages_fetched=1,
                raw_status_record_count=0,
                unique_status_context_count=0,
                warnings=[],
            ),
            rate_limit=None,
        )
    )
    return PullRequestSnapshot(
        reference=PullRequestReference(owner="octocat", repository="Hello-World", pull_number=42, canonical_url="https://github.com/octocat/Hello-World/pull/42"),
        metadata=PullRequestMetadata(
            number=42,
            title="Review action fixture",
            body="Fixture",
            state="open",
            draft=False,
            html_url="https://github.com/octocat/Hello-World/pull/42",
            author=PullRequestAuthor(login="octocat", avatar_url=None, html_url=None),
            base_branch=PullRequestBranch(ref="main", sha="base", repository_full_name="octocat/Hello-World"),
            head_branch=PullRequestBranch(ref="feature", sha="head", repository_full_name="octocat/Hello-World"),
            head_sha="head",
            created_at=BASE_TIME,
            updated_at=BASE_TIME,
            closed_at=None,
            merged_at=None,
            additions=sum(file.additions for file in classified_files),
            deletions=sum(file.deletions for file in classified_files),
            changed_files=len(classified_files),
            commit_count=1,
            mergeable=None,
            mergeable_state=None,
            labels=[],
        ),
        files=classified_files,
        commits=[PullRequestCommit(sha="commit", message="Fixture", html_url=None, author_login=None, author_name=None, authored_at=BASE_TIME, committed_at=BASE_TIME)],
        ci=ci,
        ci_explanation=build_ci_explanation(ci),
        review_context=review_context if review_context is not None else build_review_context(
            [],
            [],
            reviews_complete=True,
            comments_complete=True,
            review_pages_fetched=0,
            comment_pages_fetched=0,
            pr_author_login="octocat",
            head_sha="head",
        ),
        classification_summary=classification_summary,
        signals=signals or [],
        completeness=SnapshotCompleteness(
            files_complete=files_complete,
            commits_complete=commits_complete,
            missing_patch_count=sum(1 for file in classified_files if file.patch is None),
            warnings=[],
        ),
        fetched_at=BASE_TIME,
        rate_limit=GitHubRateLimit(limit=None, remaining=None, used=None, resource=None, reset_at=None),
    )


def analyzed_snapshot(
    files: list[ChangedFile],
    *,
    manual_signals: list[ReviewSignal] | None = None,
    ci_state: CiState = CiState.PASSING,
    ci_visibility: CiVisibility = CiVisibility.COMPLETE,
    check_runs: list[CheckRunRecord] | None = None,
    commit_statuses: list[CommitStatusRecord] | None = None,
    review_context=None,
    files_complete: bool = True,
    commits_complete: bool = True,
) -> PullRequestSnapshot:
    snapshot = base_snapshot(
        files,
        signals=manual_signals,
        ci_state=ci_state,
        ci_visibility=ci_visibility,
        check_runs=check_runs,
        commit_statuses=commit_statuses,
        review_context=review_context,
        files_complete=files_complete,
        commits_complete=commits_complete,
    )
    if manual_signals is None:
        result = analyze_snapshot_signals(snapshot)
        snapshot = snapshot.model_copy(update={"signals": result.signals, "signal_summary": result.summary})
    snapshot = snapshot.model_copy(
        update={
            "merge_risk": calculate_merge_risk(snapshot.signals),
            "evidence_confidence": calculate_evidence_confidence(snapshot),
        }
    )
    snapshot = snapshot.model_copy(update={"merge_readiness": calculate_merge_readiness(snapshot)})
    ranked_files, file_priority_summary = calculate_file_priorities(snapshot)
    return snapshot.model_copy(update={"ranked_files": ranked_files, "file_priority_summary": file_priority_summary})


def actions_by_rule(snapshot: PullRequestSnapshot) -> dict[str, ReviewAction]:
    actions, _summary = build_review_actions(snapshot)
    return {action.rule_id: action for action in actions}


def test_review_action_domain_validation_and_summary_consistency() -> None:
    assert [priority.value for priority in ReviewActionPriority] == ["high", "medium", "low"]
    assert "security" in [category.value for category in ReviewActionCategory]
    with pytest.raises(ValidationError):
        ReviewAction(
            id="bad",
            rule_id="bad",
            title="Bad",
            description="Bad",
            priority="urgent",
            category=ReviewActionCategory.CI,
            affected_files=[],
            related_signal_ids=[],
            related_readiness_rule_ids=[],
            evidence=[],
            limitations=[],
        )
    with pytest.raises(ValidationError):
        ReviewActionSummary(
            total_actions=2,
            counts_by_priority=[ReviewActionCount(name="high", count=1)],
            counts_by_category=[ReviewActionCount(name="ci", count=2)],
            affected_file_count=0,
            high_priority_action_count=1,
            rules_version="v1",
            limitations=[],
        )


def test_rule_registry_is_stable_and_complete() -> None:
    rule_ids = [rule.rule_id for rule in RULES]
    assert REVIEW_ACTION_RULES_VERSION == "v1"
    assert len(rule_ids) == len(set(rule_ids))
    assert {
        "action.resolve_merge_conflict",
        "action.inspect_failing_ci",
        "action.verify_credential_like_literal",
        "action.review_highest_priority_files",
    } <= set(rule_ids)


@pytest.mark.parametrize(
    ("ci_state", "ci_visibility", "expected"),
    [
        (CiState.FAILING, CiVisibility.COMPLETE, {"action.inspect_failing_ci"}),
        (CiState.PENDING, CiVisibility.COMPLETE, {"action.await_pending_ci"}),
        (CiState.MISSING, CiVisibility.COMPLETE, {"action.investigate_ci_visibility"}),
        (CiState.UNKNOWN, CiVisibility.COMPLETE, {"action.investigate_ci_visibility"}),
        (CiState.PASSING, CiVisibility.PARTIAL, {"action.investigate_ci_visibility"}),
        (CiState.PASSING, CiVisibility.UNAVAILABLE, {"action.investigate_ci_visibility"}),
    ],
)
def test_ci_actions_and_suppression(ci_state: CiState, ci_visibility: CiVisibility, expected: set[str]) -> None:
    actions = actions_by_rule(analyzed_snapshot([changed_file("backend/app/main.py")], ci_state=ci_state, ci_visibility=ci_visibility))

    assert expected <= set(actions)
    if "action.inspect_failing_ci" in actions:
        assert "action.await_pending_ci" not in actions
    if "action.investigate_ci_visibility" in actions:
        evidence = " ".join(actions["action.investigate_ci_visibility"].evidence)
        assert ci_visibility.value in evidence or ci_state.value in evidence


def test_failing_ci_action_and_readiness_reference_specific_surface() -> None:
    snapshot = analyzed_snapshot(
        [changed_file("backend/app/main.py")],
        check_runs=[
            CheckRunRecord(
                id=1,
                name="Static checks & unit tests",
                status="completed",
                conclusion="success",
                provider_name="GitHub Actions",
                provider_slug="github-actions",
                details_url="https://github.com/octocat/Hello-World/actions/runs/1/job/2",
                started_at=BASE_TIME,
                completed_at=BASE_TIME,
            )
        ],
        commit_statuses=[
            CommitStatusRecord(
                id=2,
                context="Vercel",
                state="failure",
                description="Authorization required to deploy.",
                target_url="https://vercel.com/git/authorize?repo=octocat",
                creator_login="vercel[bot]",
                created_at=BASE_TIME,
                updated_at=BASE_TIME,
            )
        ],
    )

    assert snapshot.merge_readiness.decision.value == "blocked"
    assert "failed Vercel authorization/configuration check" in snapshot.merge_readiness.reasons[0].explanation
    actions = actions_by_rule(snapshot)
    assert actions["action.inspect_failing_ci"].title == "Inspect failed Vercel authorization/configuration check"
    assert actions["action.inspect_failing_ci"].description == "Authorization required to deploy."
    evidence = " ".join(actions["action.inspect_failing_ci"].evidence)
    assert "Vercel" in evidence
    assert "Authorization required to deploy." in evidence
    assert "https://vercel.com/git/authorize?repo=octocat" in evidence
    assert "Passed CI item: GitHub Actions / Static checks & unit tests." in actions["action.inspect_failing_ci"].evidence


def test_failing_ci_actions_use_provider_category_titles_and_keep_scores_stable() -> None:
    snapshot = analyzed_snapshot(
        [changed_file("backend/app/main.py")],
        check_runs=[
            CheckRunRecord(
                id=10,
                name="Unit tests",
                status="completed",
                conclusion="failure",
                provider_name="github actions",
                provider_slug="github-actions",
                details_url="https://github.com/sample-org/review-console/actions/runs/1/job/10",
                started_at=BASE_TIME,
                completed_at=BASE_TIME,
            ),
            CheckRunRecord(
                id=11,
                name="Build package",
                status="completed",
                conclusion="failure",
                provider_name="GitHub Actions",
                provider_slug="github-actions",
                details_url="https://github.com/sample-org/review-console/actions/runs/1/job/11",
                started_at=BASE_TIME,
                completed_at=BASE_TIME,
            ),
        ],
    )
    actions, _summary = build_review_actions(snapshot)
    ci_actions = [action for action in actions if action.rule_id == "action.inspect_failing_ci"]

    assert [action.title for action in ci_actions] == [
        "Inspect failed GitHub Actions build check",
        "Inspect failed GitHub Actions test check",
    ]
    assert all(action.title != "Inspect failing CI" for action in ci_actions)
    assert all("github actions" not in action.title for action in ci_actions)
    assert all("GitHub Actions GitHub Actions" not in action.title for action in ci_actions)
    assert snapshot.merge_risk.score == calculate_merge_risk(snapshot.signals).score
    assert snapshot.merge_readiness.decision.value == "blocked"
    assert snapshot.evidence_confidence.score == calculate_evidence_confidence(snapshot).score


def test_equivalent_failing_ci_actions_merge_and_retain_item_evidence() -> None:
    snapshot = analyzed_snapshot(
        [changed_file("backend/app/main.py")],
        check_runs=[
            CheckRunRecord(
                id=20,
                name="Unit tests",
                status="completed",
                conclusion="failure",
                provider_name="GitHub Actions",
                provider_slug="github-actions",
                details_url="https://github.com/sample-org/review-console/actions/runs/1/job/20",
                started_at=BASE_TIME,
                completed_at=BASE_TIME,
            ),
            CheckRunRecord(
                id=21,
                name="Integration tests",
                status="completed",
                conclusion="failure",
                provider_name="github actions",
                provider_slug="github-actions",
                details_url="https://github.com/sample-org/review-console/actions/runs/1/job/21",
                started_at=BASE_TIME,
                completed_at=BASE_TIME,
            ),
        ],
    )
    actions, _summary = build_review_actions(snapshot)
    ci_actions = [action for action in actions if action.rule_id == "action.inspect_failing_ci"]

    assert len(ci_actions) == 1
    assert ci_actions[0].title == "Inspect failed GitHub Actions test check"
    assert ci_actions[0].description == "2 test checks require review while failing."
    evidence = " ".join(ci_actions[0].evidence)
    assert "Unit tests" in evidence
    assert "Integration tests" in evidence


def test_pending_ci_action_uses_specific_provider_title() -> None:
    snapshot = analyzed_snapshot(
        [changed_file("backend/app/main.py")],
        check_runs=[
            CheckRunRecord(
                id=30,
                name="Unit tests",
                status="queued",
                conclusion=None,
                provider_name="github actions",
                provider_slug="github-actions",
                details_url="https://github.com/sample-org/review-console/actions/runs/1/job/30",
                started_at=BASE_TIME,
                completed_at=None,
            )
        ],
    )
    actions = actions_by_rule(snapshot)

    assert actions["action.await_pending_ci"].title == "Inspect pending GitHub Actions test check"
    assert "github actions" not in actions["action.await_pending_ci"].title


def test_unknown_ci_provider_and_category_use_readable_fallbacks() -> None:
    unknown_category = analyzed_snapshot(
        [changed_file("backend/app/main.py")],
        check_runs=[
            CheckRunRecord(
                id=40,
                name="Custom gate",
                status="completed",
                conclusion="failure",
                provider_name="internal ci",
                provider_slug="internal-ci",
                details_url="https://ci.review-console.example/runs/40",
                started_at=BASE_TIME,
                completed_at=BASE_TIME,
            )
        ],
    )
    unknown_provider = analyzed_snapshot(
        [changed_file("backend/app/main.py")],
        check_runs=[
            CheckRunRecord(
                id=41,
                name="Custom gate",
                status="completed",
                conclusion="failure",
                provider_name=None,
                provider_slug=None,
                details_url="https://ci.review-console.example/runs/41",
                started_at=BASE_TIME,
                completed_at=BASE_TIME,
            )
        ],
    )

    assert actions_by_rule(unknown_category)["action.inspect_failing_ci"].title == "Inspect failed Internal CI check"
    assert "unknown check check" not in actions_by_rule(unknown_category)["action.inspect_failing_ci"].title
    assert actions_by_rule(unknown_provider)["action.inspect_failing_ci"].title == "Inspect failed GitHub Checks check"


def test_review_concern_lifecycle_actions_are_deduplicated_traceable_and_non_scoring() -> None:
    review_context = build_review_context(
        [review_record(900, "reviewer", ReviewState.CHANGES_REQUESTED)],
        [
            review_comment(901, "reviewer", "Please fix this.", path="backend/app/main.py"),
            review_comment(902, "octocat", "Fixed.", created_at=BASE_TIME.replace(minute=1), in_reply_to_id=901),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=1,
        comment_pages_fetched=1,
        pr_author_login="octocat",
        head_sha="head",
    )
    snapshot = analyzed_snapshot([changed_file("backend/app/main.py")], review_context=review_context)

    before_risk = snapshot.merge_risk.score
    before_readiness = snapshot.merge_readiness.decision
    actions, _summary = build_review_actions(snapshot)
    review_actions = [action for action in actions if action.category == ReviewActionCategory.REVIEW]

    assert len(review_actions) == 1
    assert review_actions[0].rule_id == "action.review_concern.active_change_request"
    assert review_actions[0].affected_files == ["backend/app/main.py"]
    assert any("Details URL: https://github.com/octocat/Hello-World/pull/42#discussion_r901" in item for item in review_actions[0].evidence)
    assert any("cannot verify" in item for item in review_actions[0].evidence)
    assert snapshot.merge_risk.score == before_risk
    assert snapshot.merge_readiness.decision == before_readiness


def test_author_claimed_addressed_action_is_emitted_without_active_change_request() -> None:
    review_context = build_review_context(
        [review_record(900, "reviewer", ReviewState.COMMENTED)],
        [
            review_comment(901, "reviewer", "Please revise this.", path="backend/app/main.py"),
            review_comment(902, "octocat", "Addressed.", created_at=BASE_TIME.replace(minute=1), in_reply_to_id=901),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=1,
        comment_pages_fetched=1,
        pr_author_login="octocat",
        head_sha="head",
    )
    snapshot = analyzed_snapshot([changed_file("backend/app/main.py")], review_context=review_context)

    actions = actions_by_rule(snapshot)

    assert "action.review_concern.verify_author_claim" in actions
    action = actions["action.review_concern.verify_author_claim"]
    assert action.id == "action.review_concern.verify_author_claim.901"
    assert action.priority == ReviewActionPriority.MEDIUM
    assert any("cannot verify" in item for item in action.evidence)


def test_security_actions_are_distinct_and_sanitized() -> None:
    snapshot = analyzed_snapshot(
        [
            changed_file("backend/app/security/secrets.py", patch="+password = 'not-a-real-secret-fixture'\n"),
            changed_file("backend/app/security/settings.py", patch="+verify=False\n"),
        ]
    )
    actions = actions_by_rule(snapshot)
    serialized = " ".join(action.model_dump_json() for action in actions.values())

    assert "action.verify_credential_like_literal" in actions
    assert "action.verify_security_control_setting" in actions
    assert "not-a-real-secret-fixture" not in serialized
    assert "password =" not in serialized
    assert "DISABLE_SSL_VERIFY = true" not in serialized


def test_required_signal_actions_are_emitted() -> None:
    snapshot = analyzed_snapshot(
        [
            changed_file("database/migrations/001_drop_users.sql", patch=None),
            changed_file("backend/app/config/settings.py"),
            changed_file("package.json"),
            changed_file("infra/main.tf"),
            changed_file("backend/app/main.py", additions=600, deletions=500, changes=1100),
            changed_file("backend/app/service.py", patch="+print('debug')\n+# TODO: fixture\n"),
            changed_file("dist/generated.pb.py", additions=600, deletions=0, changes=600, patch=None),
            changed_file("backend/app/auth/session.py"),
            changed_file("tests/test_session.py", status="removed"),
        ],
        commits_complete=False,
    )
    actions = actions_by_rule(snapshot)

    assert {
        "action.inspect_migration_without_patch",
        "action.review_runtime_configuration",
        "action.review_dependency_manifest",
        "action.review_infrastructure_change",
        "action.review_large_change_scope",
        "action.inspect_incomplete_evidence",
        "action.review_code_quality_hints",
        "action.review_generated_or_opaque_changes",
        "action.review_deleted_tests",
        "action.review_highest_priority_files",
    } <= set(actions)


def test_plain_typescript_actions_are_traceable_and_do_not_emit_unrelated_sensitive_actions() -> None:
    snapshot = analyzed_snapshot(
        [
            changed_file("frontend/src/components/PullRequestCard.tsx", additions=40, deletions=4, changes=44, patch="+export function PullRequestCard() {}\n"),
            changed_file("frontend/src/hooks/usePullRequest.ts", additions=18, deletions=2, changes=20, patch="+export function usePullRequest() {}\n"),
            changed_file("frontend/src/utils/formatPullRequest.ts", additions=12, deletions=3, changes=15, patch="+export function formatPullRequest() {}\n"),
        ],
        ci_state=CiState.FAILING,
    )
    actions, summary = build_review_actions(snapshot)
    actions_by_id = {action.rule_id: action for action in actions}
    forbidden_actions = {
        "action.verify_credential_like_literal",
        "action.verify_security_control_setting",
        "action.inspect_destructive_migration",
        "action.inspect_migration_without_patch",
    }
    signal_ids = {signal.id for signal in snapshot.signals}
    changed_paths = {file.filename for file in snapshot.files}

    assert "action.inspect_failing_ci" in actions_by_id
    assert "action.review_production_change_tests" in actions_by_id
    assert "action.review_highest_priority_files" in actions_by_id
    assert forbidden_actions.isdisjoint(actions_by_id)
    assert summary.total_actions == len(actions)
    for action in actions:
        assert set(action.related_signal_ids) <= signal_ids
        assert set(action.affected_files) <= changed_paths


def test_merge_conflict_destructive_migration_and_sensitive_rename_actions() -> None:
    snapshot = analyzed_snapshot(
        [
            changed_file("database/migrations/002_drop_accounts.sql", patch="+DROP TABLE accounts;\n"),
            changed_file("backend/app/auth/roles.py", status="renamed", previous_filename="tests/test_roles.py"),
        ]
    )
    snapshot = snapshot.model_copy(update={"metadata": snapshot.metadata.model_copy(update={"mergeable": False, "mergeable_state": "dirty"})})
    result = analyze_snapshot_signals(snapshot)
    snapshot = snapshot.model_copy(update={"signals": result.signals, "signal_summary": result.summary})
    snapshot = snapshot.model_copy(update={"merge_risk": calculate_merge_risk(snapshot.signals), "evidence_confidence": calculate_evidence_confidence(snapshot)})
    snapshot = snapshot.model_copy(update={"merge_readiness": calculate_merge_readiness(snapshot)})
    ranked_files, file_priority_summary = calculate_file_priorities(snapshot)
    snapshot = snapshot.model_copy(update={"ranked_files": ranked_files, "file_priority_summary": file_priority_summary})
    actions = actions_by_rule(snapshot)

    assert "action.resolve_merge_conflict" in actions
    assert "action.inspect_destructive_migration" in actions
    assert "action.review_sensitive_rename" in actions


def test_top_five_ranked_file_baseline_and_file_ordering() -> None:
    ranked_files = [
        RankedFile(rank=3, path="c.py", previous_path=None, status="modified", score=10, level=FilePriorityLevel.LOW, primary_kind="source", areas=[], language="python", changes=1, additions=1, deletions=0, related_signal_ids=[], factors=[], limitations=[]),
        RankedFile(rank=1, path="a.py", previous_path=None, status="modified", score=90, level=FilePriorityLevel.VERY_HIGH, primary_kind="source", areas=[], language="python", changes=1, additions=1, deletions=0, related_signal_ids=[], factors=[], limitations=[]),
        RankedFile(rank=2, path="b.py", previous_path=None, status="modified", score=80, level=FilePriorityLevel.VERY_HIGH, primary_kind="source", areas=[], language="python", changes=1, additions=1, deletions=0, related_signal_ids=[], factors=[], limitations=[]),
        RankedFile(rank=4, path="d.py", previous_path=None, status="modified", score=9, level=FilePriorityLevel.LOW, primary_kind="source", areas=[], language="python", changes=1, additions=1, deletions=0, related_signal_ids=[], factors=[], limitations=[]),
        RankedFile(rank=5, path="e.py", previous_path=None, status="modified", score=8, level=FilePriorityLevel.LOW, primary_kind="source", areas=[], language="python", changes=1, additions=1, deletions=0, related_signal_ids=[], factors=[], limitations=[]),
        RankedFile(rank=6, path="f.py", previous_path=None, status="modified", score=7, level=FilePriorityLevel.LOW, primary_kind="source", areas=[], language="python", changes=1, additions=1, deletions=0, related_signal_ids=[], factors=[], limitations=[]),
    ]
    snapshot = analyzed_snapshot([changed_file(file.path) for file in ranked_files]).model_copy(update={"ranked_files": ranked_files})
    actions = actions_by_rule(snapshot)

    baseline = actions["action.review_highest_priority_files"]
    assert baseline.affected_files == ["a.py", "b.py", "c.py", "d.py", "e.py"]
    assert "must not be ignored" in " ".join(baseline.evidence)


def test_deterministic_ordering_and_unknown_signal_ignored() -> None:
    signals = [
        manual_signal("unknown.future", signal_id="z", affected_files=["z.py"]),
        manual_signal("code_quality.todo_or_fixme_added", signal_id="b", affected_files=["b.py"]),
        manual_signal("code_quality.debug_statement_added", signal_id="a", affected_files=["a.py"]),
    ]
    first = analyzed_snapshot([changed_file("b.py"), changed_file("a.py")], manual_signals=signals)
    second = analyzed_snapshot([changed_file("a.py"), changed_file("b.py")], manual_signals=list(reversed(signals))).model_copy(
        update={"ranked_files": first.ranked_files}
    )

    assert [action.model_dump() for action in build_review_actions(first)[0]] == [
        action.model_dump() for action in build_review_actions(second)[0]
    ]
    actions = actions_by_rule(first)
    assert "unknown.future" not in " ".join(action.model_dump_json() for action in actions.values())
    assert len(actions) == len(set(actions))
