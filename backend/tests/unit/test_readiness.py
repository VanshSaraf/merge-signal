from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.file_classification import FileKind
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
)
from app.domain.readiness import DecisionEffect, DecisionReason, MergeReadinessAssessment, MergeReadinessDecision
from app.domain.review_signal import EvidenceKind, ReviewSignal, SignalCategory, SignalEvidence, SignalScope, SignalSeverity
from app.readiness.engine import calculate_merge_readiness
from app.readiness.rules import READINESS_RULES_VERSION
from app.scoring import calculate_evidence_confidence, calculate_merge_risk
from app.services.file_classifier import classify_changed_files

BASE_TIME = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)


def signal(
    rule_id: str,
    *,
    signal_id: str | None = None,
    severity: SignalSeverity = SignalSeverity.MEDIUM,
    category: SignalCategory = SignalCategory.CHANGE_SCOPE,
    affected_files: list[str] | None = None,
) -> ReviewSignal:
    return ReviewSignal(
        id=signal_id or f"{rule_id}:0",
        rule_id=rule_id,
        title=f"Observed {rule_id}",
        description="Observed deterministic fixture signal.",
        category=category,
        severity=severity,
        scope=SignalScope.FILE_SET,
        affected_files=affected_files or [],
        evidence=[
            SignalEvidence(
                kind=EvidenceKind.PATCH_PATTERN,
                message="Fixture evidence.",
                observed_value="sanitized_fixture_value",
            )
        ],
        limitations=[],
        tags=["fixture"],
    )


def changed_file(filename: str = "backend/app/main.py", *, patch: str | None = "@@ -1 +1 @@\n-old\n+new") -> ChangedFile:
    return ChangedFile(
        filename=filename,
        status="modified",
        additions=1,
        deletions=1,
        changes=2,
        patch=patch,
        previous_filename=None,
        blob_url=None,
    )


def snapshot(
    *,
    signals: list[ReviewSignal] | None = None,
    files: list[ChangedFile] | None = None,
    draft: bool = False,
    ci_state: CiState = CiState.PASSING,
    ci_visibility: CiVisibility = CiVisibility.COMPLETE,
    files_complete: bool = True,
    commits_complete: bool = True,
) -> PullRequestSnapshot:
    files = [changed_file()] if files is None else files
    signals = [] if signals is None else signals
    classified_files, classification_summary = classify_changed_files(files)
    base = PullRequestSnapshot(
        reference=PullRequestReference(
            owner="octocat",
            repository="Hello-World",
            pull_number=42,
            canonical_url="https://github.com/octocat/Hello-World/pull/42",
        ),
        metadata=PullRequestMetadata(
            number=42,
            title="Readiness fixture",
            body="Fixture",
            state="open",
            draft=draft,
            html_url="https://github.com/octocat/Hello-World/pull/42",
            author=PullRequestAuthor(login="octocat", avatar_url=None, html_url=None),
            base_branch=PullRequestBranch(ref="main", sha="base", repository_full_name="octocat/Hello-World"),
            head_branch=PullRequestBranch(ref="feature", sha="head", repository_full_name="octocat/Hello-World"),
            head_sha="head",
            created_at=BASE_TIME,
            updated_at=BASE_TIME,
            closed_at=None,
            merged_at=None,
            additions=2,
            deletions=2,
            changed_files=len(classified_files),
            commit_count=1,
            mergeable=None,
            mergeable_state=None,
            labels=[],
        ),
        files=classified_files,
        commits=[
            PullRequestCommit(
                sha="commit",
                message="Fixture",
                html_url=None,
                author_login=None,
                author_name=None,
                authored_at=BASE_TIME,
                committed_at=BASE_TIME,
            )
        ],
        ci=PullRequestCi(
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
        ),
        classification_summary=classification_summary,
        signals=signals,
        completeness=SnapshotCompleteness(
            files_complete=files_complete,
            commits_complete=commits_complete,
            missing_patch_count=sum(1 for file in classified_files if file.patch is None),
            warnings=[],
        ),
        fetched_at=BASE_TIME,
        rate_limit=GitHubRateLimit(limit=None, remaining=None, used=None, resource=None, reset_at=None),
    )
    scored = base.model_copy(
        update={
            "merge_risk": calculate_merge_risk(signals),
            "evidence_confidence": calculate_evidence_confidence(base),
        }
    )
    return scored


def readiness(**kwargs) -> MergeReadinessAssessment:
    return calculate_merge_readiness(snapshot(**kwargs))


def rule_ids(assessment: MergeReadinessAssessment) -> list[str]:
    return [reason.rule_id for reason in assessment.reasons]


def test_readiness_domain_values_and_validation() -> None:
    assert [decision.value for decision in MergeReadinessDecision] == ["ready", "ready_with_caution", "not_ready", "blocked"]
    assert [effect.value for effect in DecisionEffect] == ["block", "require_resolution", "caution", "context"]
    reason = DecisionReason(
        rule_id="readiness.ready_baseline",
        title="Ready",
        description="Fixture.",
        effect=DecisionEffect.CONTEXT,
        observed_value="ready",
        related_signal_ids=["b", "a"],
        affected_files=["b.py", "a.py"],
        explanation="Fixture.",
        limitations=[],
    )
    assert reason.model_dump()["effect"] == "context"
    with pytest.raises(ValidationError):
        DecisionReason(
            rule_id="x",
            title="x",
            description="x",
            effect="unsupported",
            observed_value="x",
            related_signal_ids=[],
            affected_files=[],
            explanation="x",
            limitations=[],
        )
    with pytest.raises(ValidationError):
        MergeReadinessAssessment(
            decision="ready",
            decisive_rule_id="",
            reasons=[reason],
            blocking_reason_count=0,
            resolution_reason_count=0,
            caution_reason_count=0,
            context_reason_count=1,
            rules_version="v1",
            limitations=[],
        )
    with pytest.raises(ValidationError):
        MergeReadinessAssessment(
            decision="ready",
            decisive_rule_id="readiness.ready_baseline",
            reasons=[reason],
            blocking_reason_count=-1,
            resolution_reason_count=0,
            caution_reason_count=0,
            context_reason_count=1,
            rules_version="v1",
            limitations=[],
        )


def test_ready_baseline() -> None:
    assessment = readiness()
    assert assessment.decision == "ready"
    assert assessment.decisive_rule_id == "readiness.ready_baseline"
    assert rule_ids(assessment) == ["readiness.ready_baseline"]
    assert assessment.context_reason_count == 1
    assert "Ready does not mean safe or bug-free." in assessment.limitations
    assert assessment.rules_version == READINESS_RULES_VERSION


def test_blocking_rules_and_decisive_priority() -> None:
    assessment = readiness(
        signals=[
            signal("ci.failing", severity=SignalSeverity.HIGH, category=SignalCategory.CI),
            signal("metadata.merge_conflict_observed", severity=SignalSeverity.HIGH, category=SignalCategory.METADATA),
        ],
        ci_state=CiState.FAILING,
    )
    assert assessment.decision == "blocked"
    assert assessment.decisive_rule_id == "readiness.blocked.merge_conflict"
    assert rule_ids(assessment)[:2] == ["readiness.blocked.merge_conflict", "readiness.blocked.ci_failing"]
    assert assessment.blocking_reason_count == 2


@pytest.mark.parametrize(
    ("state", "visibility"),
    [
        (CiState.PENDING, CiVisibility.COMPLETE),
        (CiState.MISSING, CiVisibility.COMPLETE),
        (CiState.UNKNOWN, CiVisibility.COMPLETE),
        (CiState.UNKNOWN, CiVisibility.UNAVAILABLE),
    ],
)
def test_non_failing_ci_states_do_not_block(state: CiState, visibility: CiVisibility) -> None:
    assessment = readiness(ci_state=state, ci_visibility=visibility)
    assert assessment.decision != "blocked"


def test_failing_ci_with_partial_visibility_keeps_caution_reason() -> None:
    assessment = readiness(ci_state=CiState.FAILING, ci_visibility=CiVisibility.PARTIAL)
    assert assessment.decision == "blocked"
    assert "readiness.blocked.ci_failing" in rule_ids(assessment)
    assert "readiness.caution.ci_partial_visibility" in rule_ids(assessment)


def test_not_ready_rules_and_security_sanitization() -> None:
    assessment = readiness(
        signals=[
            signal("security.credential_like_literal_added", severity=SignalSeverity.HIGH, category=SignalCategory.SECURITY, affected_files=["b.py", "a.py", "a.py"]),
            signal("security.security_control_disabled_hint", severity=SignalSeverity.HIGH, category=SignalCategory.SECURITY),
        ]
    )
    serialized = assessment.model_dump_json()
    assert assessment.decision == "not_ready"
    assert "readiness.not_ready.credential_like_literal" in rule_ids(assessment)
    assert "readiness.not_ready.security_control_disabled" in rule_ids(assessment)
    assert "password =" not in serialized
    assert "not-a-real-secret-fixture" not in serialized
    credential_reason = next(reason for reason in assessment.reasons if reason.rule_id == "readiness.not_ready.credential_like_literal")
    assert credential_reason.affected_files == ["a.py", "b.py"]
    assert credential_reason.related_signal_ids == ["security.credential_like_literal_added:0"]


def test_not_ready_priority_independent_of_signal_order() -> None:
    signals = [
        signal("security.security_control_disabled_hint", severity=SignalSeverity.HIGH, category=SignalCategory.SECURITY),
        signal("security.credential_like_literal_added", severity=SignalSeverity.HIGH, category=SignalCategory.SECURITY),
    ]
    first = readiness(signals=signals, draft=True, ci_state=CiState.PENDING)
    second = readiness(signals=list(reversed(signals)), draft=True, ci_state=CiState.PENDING)
    assert first.model_dump() == second.model_dump()
    assert first.decision == "not_ready"
    assert first.decisive_rule_id == "readiness.not_ready.draft"


def test_low_confidence_and_incomplete_files_do_not_change_risk() -> None:
    snap = snapshot(files=[changed_file("unknown.one", patch=None)], files_complete=False, commits_complete=False, ci_visibility=CiVisibility.UNAVAILABLE, ci_state=CiState.UNKNOWN)
    risk_before = snap.merge_risk.model_dump()
    confidence_before = snap.evidence_confidence.model_dump()
    assessment = calculate_merge_readiness(snap)
    assert assessment.decision == "not_ready"
    assert snap.merge_risk.model_dump() == risk_before
    assert snap.evidence_confidence.model_dump() == confidence_before
    assert "readiness.not_ready.file_collection_incomplete" in rule_ids(assessment)
    assert "readiness.not_ready.low_evidence_confidence" in rule_ids(assessment)


def test_caution_rules_produce_ready_with_caution() -> None:
    assessment = readiness(
        signals=[
            signal("database.destructive_migration_hint", severity=SignalSeverity.HIGH, category=SignalCategory.DATABASE),
            signal("testing.sensitive_change_without_test_files", severity=SignalSeverity.HIGH, category=SignalCategory.TESTING),
            signal("testing.test_files_deleted", severity=SignalSeverity.HIGH, category=SignalCategory.TESTING),
            signal("configuration.runtime_configuration_changed", severity=SignalSeverity.MEDIUM, category=SignalCategory.CONFIGURATION),
        ],
        ci_visibility=CiVisibility.PARTIAL,
    )
    assert assessment.decision == "ready_with_caution"
    assert "readiness.caution.ci_partial_visibility" in rule_ids(assessment)
    assert "readiness.caution.destructive_migration_hint" in rule_ids(assessment)
    assert "readiness.caution.sensitive_change_without_tests" in rule_ids(assessment)
    assert "readiness.caution.test_files_deleted" in rule_ids(assessment)
    assert "readiness.caution.runtime_configuration_change" in rule_ids(assessment)


@pytest.mark.parametrize(
    ("signals", "expected_rule"),
    [
        (
            [
                signal("scope.very_large_file_count", severity=SignalSeverity.HIGH),
                signal("scope.very_large_line_churn", severity=SignalSeverity.HIGH),
                signal("authentication.paths_changed", severity=SignalSeverity.HIGH, category=SignalCategory.AUTHENTICATION),
                signal("authorization.paths_changed", severity=SignalSeverity.HIGH, category=SignalCategory.AUTHORIZATION),
                signal("database.migration_changed", severity=SignalSeverity.HIGH, category=SignalCategory.DATABASE),
                signal("dependencies.manifest_without_lockfile", severity=SignalSeverity.MEDIUM, category=SignalCategory.DEPENDENCIES),
            ],
            "readiness.caution.high_risk",
        ),
        (
            [
                signal("scope.large_file_count", severity=SignalSeverity.MEDIUM),
                signal("scope.large_line_churn", severity=SignalSeverity.MEDIUM),
                signal("metadata.large_commit_count", severity=SignalSeverity.LOW),
                signal("dependencies.manifest_without_lockfile", severity=SignalSeverity.MEDIUM, category=SignalCategory.DEPENDENCIES),
            ],
            "readiness.caution.moderate_risk",
        ),
    ],
)
def test_risk_caution_rules(signals: list[ReviewSignal], expected_rule: str) -> None:
    assessment = readiness(signals=signals)
    assert assessment.decision == "ready_with_caution"
    assert expected_rule in rule_ids(assessment)


def test_confidence_and_collection_caution_rules() -> None:
    partial_patch = readiness(files=[changed_file("backend/app/main.py", patch=None), changed_file("backend/app/other.py")])
    assert partial_patch.decision == "ready_with_caution"
    assert "readiness.caution.patch_visibility_partial" in rule_ids(partial_patch)

    missing_ci = readiness(ci_state=CiState.MISSING, ci_visibility=CiVisibility.COMPLETE)
    assert missing_ci.decision == "ready_with_caution"
    assert "readiness.caution.ci_missing" in rule_ids(missing_ci)

    commit_partial = readiness(commits_complete=False)
    assert commit_partial.decision == "ready_with_caution"
    assert "readiness.caution.commit_collection_incomplete" in rule_ids(commit_partial)


def test_precedence_matrix() -> None:
    assert readiness(signals=[signal("metadata.merge_conflict_observed", severity=SignalSeverity.HIGH)], ci_state=CiState.FAILING).decision == "blocked"
    assert readiness(draft=True, ci_state=CiState.FAILING).decision == "blocked"
    assert readiness(draft=True, ci_state=CiState.PENDING).decisive_rule_id == "readiness.not_ready.draft"
    assert readiness(signals=[signal("scope.very_large_file_count", severity=SignalSeverity.HIGH), signal("scope.very_large_line_churn", severity=SignalSeverity.HIGH)], ci_state=CiState.PENDING).decision == "not_ready"
    assert readiness(signals=[signal("scope.very_large_file_count", severity=SignalSeverity.HIGH), signal("scope.very_large_line_churn", severity=SignalSeverity.HIGH)]).decision == "ready"
    very_high = readiness(
        signals=[
            signal("scope.very_large_file_count", severity=SignalSeverity.HIGH),
            signal("scope.very_large_line_churn", severity=SignalSeverity.HIGH),
            signal("authentication.paths_changed", severity=SignalSeverity.HIGH, category=SignalCategory.AUTHENTICATION),
            signal("authorization.paths_changed", severity=SignalSeverity.HIGH, category=SignalCategory.AUTHORIZATION),
            signal("database.migration_changed", severity=SignalSeverity.HIGH, category=SignalCategory.DATABASE),
            signal("database.destructive_migration_hint", severity=SignalSeverity.HIGH, category=SignalCategory.DATABASE),
            signal("testing.sensitive_change_without_test_files", severity=SignalSeverity.HIGH, category=SignalCategory.TESTING),
            signal("dependencies.manifest_without_lockfile", severity=SignalSeverity.MEDIUM, category=SignalCategory.DEPENDENCIES),
            signal("infrastructure.configuration_changed", severity=SignalSeverity.MEDIUM, category=SignalCategory.INFRASTRUCTURE),
            signal("configuration.runtime_configuration_changed", severity=SignalSeverity.MEDIUM, category=SignalCategory.CONFIGURATION),
            signal("code_quality.empty_exception_handler_added", severity=SignalSeverity.MEDIUM, category=SignalCategory.CODE_QUALITY),
        ]
    )
    assert very_high.decision == "not_ready"
    assert very_high.decisive_rule_id == "readiness.not_ready.very_high_risk"
    assert readiness(ci_state=CiState.MISSING, ci_visibility=CiVisibility.COMPLETE).decision == "ready_with_caution"
    assert readiness().decision == "ready"


def test_suppression_behavior() -> None:
    very_high = readiness(
        signals=[
            signal("scope.very_large_file_count", severity=SignalSeverity.HIGH),
            signal("scope.very_large_line_churn", severity=SignalSeverity.HIGH),
            signal("authentication.paths_changed", severity=SignalSeverity.HIGH, category=SignalCategory.AUTHENTICATION),
            signal("authorization.paths_changed", severity=SignalSeverity.HIGH, category=SignalCategory.AUTHORIZATION),
            signal("database.migration_changed", severity=SignalSeverity.HIGH, category=SignalCategory.DATABASE),
            signal("database.destructive_migration_hint", severity=SignalSeverity.HIGH, category=SignalCategory.DATABASE),
            signal("testing.sensitive_change_without_test_files", severity=SignalSeverity.HIGH, category=SignalCategory.TESTING),
            signal("dependencies.manifest_without_lockfile", severity=SignalSeverity.MEDIUM, category=SignalCategory.DEPENDENCIES),
            signal("infrastructure.configuration_changed", severity=SignalSeverity.MEDIUM, category=SignalCategory.INFRASTRUCTURE),
            signal("configuration.runtime_configuration_changed", severity=SignalSeverity.MEDIUM, category=SignalCategory.CONFIGURATION),
            signal("code_quality.empty_exception_handler_added", severity=SignalSeverity.MEDIUM, category=SignalCategory.CODE_QUALITY),
        ],
    )
    assert "readiness.not_ready.very_high_risk" in rule_ids(very_high)
    assert "readiness.caution.high_risk" not in rule_ids(very_high)
    assert "readiness.caution.moderate_risk" not in rule_ids(very_high)

    unavailable = readiness(ci_state=CiState.UNKNOWN, ci_visibility=CiVisibility.UNAVAILABLE)
    assert "readiness.not_ready.ci_unavailable" in rule_ids(unavailable)
    assert "readiness.caution.ci_unknown" not in rule_ids(unavailable)
    assert "readiness.caution.ci_missing" not in rule_ids(unavailable)
    assert "readiness.ready_baseline" not in rule_ids(unavailable)


def test_binary_only_ready_and_missing_ci_caution() -> None:
    binary_file = changed_file("assets/logo.png", patch=None)
    assert classify_changed_files([binary_file])[0][0].classification.primary_kind == FileKind.ASSET
    ready_assessment = readiness(files=[binary_file])
    assert ready_assessment.decision == "ready"

    missing_ci = readiness(files=[binary_file], ci_state=CiState.MISSING)
    assert missing_ci.decision == "ready_with_caution"
