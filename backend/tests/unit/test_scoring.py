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
from app.domain.review_signal import EvidenceKind, ReviewSignal, SignalCategory, SignalEvidence, SignalScope, SignalSeverity
from app.domain.scoring import ConfidenceComponent, ConfidenceComponentStatus, MergeRiskAssessment, RiskGroup, RiskGroupScore
from app.scoring.confidence_engine import calculate_evidence_confidence, level_for_evidence_confidence
from app.scoring.risk_engine import calculate_merge_risk, level_for_merge_risk
from app.scoring.risk_rules import RISK_GROUP_CAPS, RISK_RULE_BY_ID, RISK_RULE_WEIGHTS, SCORING_RULES_VERSION
from app.services.file_classifier import classify_changed_files
from app.signals.rules import RULE_BY_ID

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
        evidence=[SignalEvidence(kind=EvidenceKind.METADATA, message="Fixture evidence.")],
        limitations=[],
        tags=["fixture"],
    )


def changed_file(filename: str, *, patch: str | None = "@@ -1 +1 @@\n-old\n+new") -> ChangedFile:
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
    files: list[ChangedFile],
    *,
    files_complete: bool = True,
    commits_complete: bool = True,
    ci_visibility: CiVisibility = CiVisibility.COMPLETE,
    ci_state: CiState = CiState.PASSING,
) -> PullRequestSnapshot:
    classified_files, classification_summary = classify_changed_files(files)
    return PullRequestSnapshot(
        reference=PullRequestReference(
            owner="octocat",
            repository="Hello-World",
            pull_number=42,
            canonical_url="https://github.com/octocat/Hello-World/pull/42",
        ),
        metadata=PullRequestMetadata(
            number=42,
            title="Scoring fixture",
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
        completeness=SnapshotCompleteness(
            files_complete=files_complete,
            commits_complete=commits_complete,
            missing_patch_count=sum(1 for file in classified_files if file.patch is None),
            warnings=[],
        ),
        fetched_at=BASE_TIME,
        rate_limit=GitHubRateLimit(limit=None, remaining=None, used=None, resource=None, reset_at=None),
    )


@pytest.mark.parametrize(
    ("score", "level"),
    [(0, "low"), (24, "low"), (25, "moderate"), (49, "moderate"), (50, "high"), (74, "high"), (75, "very_high"), (100, "very_high")],
)
def test_merge_risk_level_boundaries(score: int, level: str) -> None:
    assert level_for_merge_risk(score) == level


@pytest.mark.parametrize(
    ("score", "level"),
    [(0, "low"), (49, "low"), (50, "medium"), (79, "medium"), (80, "high"), (100, "high")],
)
def test_evidence_confidence_level_boundaries(score: int, level: str) -> None:
    assert level_for_evidence_confidence(score) == level


def test_scoring_domain_validation_and_serialization() -> None:
    assert [group.value for group in RiskGroup] == ["change_scope", "sensitive_systems", "testing", "ci", "operational_change", "code_quality"]
    assert [status.value for status in ConfidenceComponentStatus] == ["complete", "partial", "unavailable", "not_applicable"]
    assert ConfidenceComponent(
        id="fixture",
        name="Fixture",
        maximum_points=1,
        awarded_points=1,
        status=ConfidenceComponentStatus.COMPLETE,
        explanation="Fixture.",
        limitations=[],
    ).model_dump()["status"] == "complete"
    with pytest.raises(ValidationError):
        MergeRiskAssessment(
            score=-1,
            level="low",
            max_score=100,
            group_scores=[],
            contributions=[],
            contributing_signal_count=0,
            non_scoring_signal_count=0,
            rules_version="v1",
            limitations=[],
        )
    with pytest.raises(ValidationError):
        RiskGroupScore(group=RiskGroup.CI, raw_points=1, applied_points=2, cap=1, capped_points=0, contribution_count=1)


def test_risk_registry_references_real_signal_rules_and_caps_total_100() -> None:
    assert SCORING_RULES_VERSION == "v1"
    assert sum(RISK_GROUP_CAPS.values()) == 100
    assert len(RISK_RULE_BY_ID) == len(RISK_RULE_WEIGHTS)
    for configured in RISK_RULE_WEIGHTS:
        assert configured.rule_id in RULE_BY_ID
        assert configured.points >= 0
        assert configured.group in RiskGroup
    for rule_id in ["metadata.draft_pull_request", "testing.only_test_or_documentation_changes", "completeness.file_collection_incomplete"]:
        assert RISK_RULE_BY_ID[rule_id].points == 0


def test_no_signals_produces_zero_risk_with_all_groups_present() -> None:
    assessment = calculate_merge_risk([])
    assert assessment.score == 0
    assert assessment.level == "low"
    assert [group.group for group in assessment.group_scores] == list(RiskGroup)
    assert assessment.contributions == []


def test_group_caps_partial_and_full_capping_are_deterministic() -> None:
    signals = [
        signal("authentication.paths_changed", severity=SignalSeverity.HIGH, category=SignalCategory.AUTHENTICATION),
        signal("authorization.paths_changed", severity=SignalSeverity.HIGH, category=SignalCategory.AUTHORIZATION),
        signal("security.credential_like_literal_added", severity=SignalSeverity.HIGH, category=SignalCategory.SECURITY),
    ]
    reversed_assessment = calculate_merge_risk(list(reversed(signals)))
    assessment = calculate_merge_risk(signals)
    assert assessment.model_dump() == reversed_assessment.model_dump()
    assert assessment.score == 25
    contributions = {contribution.rule_id: contribution for contribution in assessment.contributions}
    assert contributions["security.credential_like_literal_added"].applied_points == 18
    assert contributions["authentication.paths_changed"].applied_points == 7
    assert contributions["authorization.paths_changed"].applied_points == 0
    assert contributions["authorization.paths_changed"].capped is True


def test_representative_multi_group_risk_and_unknown_signal() -> None:
    assessment = calculate_merge_risk(
        [
            signal("scope.very_large_file_count", severity=SignalSeverity.HIGH),
            signal("scope.very_large_line_churn", severity=SignalSeverity.HIGH),
            signal("database.destructive_migration_hint", severity=SignalSeverity.HIGH, category=SignalCategory.DATABASE),
            signal("testing.sensitive_change_without_test_files", severity=SignalSeverity.HIGH, category=SignalCategory.TESTING),
            signal("ci.failing", severity=SignalSeverity.HIGH, category=SignalCategory.CI),
            signal("ci.partial_visibility", severity=SignalSeverity.MEDIUM, category=SignalCategory.CI),
            signal("dependencies.manifest_without_lockfile", severity=SignalSeverity.MEDIUM, category=SignalCategory.DEPENDENCIES),
            signal("code_quality.empty_exception_handler_added", severity=SignalSeverity.MEDIUM, category=SignalCategory.CODE_QUALITY),
            signal("future.informational", severity=SignalSeverity.INFO),
        ]
    )
    assert assessment.score == 78
    assert assessment.level == "very_high"
    assert assessment.non_scoring_signal_count == 1
    assert sum(group.applied_points for group in assessment.group_scores) == assessment.score


def test_low_risk_high_confidence_documentation_only() -> None:
    risk = calculate_merge_risk([signal("testing.only_test_or_documentation_changes", severity=SignalSeverity.INFO)])
    confidence = calculate_evidence_confidence(snapshot([changed_file("docs/readme.md")]))
    assert risk.score == 0
    assert risk.level == "low"
    assert confidence.score == 100
    assert confidence.level == "high"


def test_high_risk_high_confidence_remains_independent() -> None:
    risk = calculate_merge_risk(
        [
            signal("database.destructive_migration_hint", severity=SignalSeverity.HIGH, category=SignalCategory.DATABASE),
            signal("testing.sensitive_change_without_test_files", severity=SignalSeverity.HIGH, category=SignalCategory.TESTING),
            signal("ci.failing", severity=SignalSeverity.HIGH, category=SignalCategory.CI),
            signal("scope.very_large_line_churn", severity=SignalSeverity.HIGH),
        ]
    )
    confidence = calculate_evidence_confidence(snapshot([changed_file("backend/app/main.py")], ci_state=CiState.FAILING))
    assert risk.score == 60
    assert risk.level == "high"
    assert confidence.score == 100
    assert confidence.level == "high"


def test_high_risk_low_confidence_remains_independent() -> None:
    risk = calculate_merge_risk(
        [
            signal("security.credential_like_literal_added", severity=SignalSeverity.HIGH, category=SignalCategory.SECURITY),
            signal("testing.sensitive_change_without_test_files", severity=SignalSeverity.HIGH, category=SignalCategory.TESTING),
            signal("ci.failing", severity=SignalSeverity.HIGH, category=SignalCategory.CI),
            signal("scope.very_large_file_count", severity=SignalSeverity.HIGH),
        ]
    )
    confidence = calculate_evidence_confidence(
        snapshot(
            [changed_file("backend/auth/permissions.py", patch=None)],
            files_complete=False,
            commits_complete=False,
            ci_visibility=CiVisibility.UNAVAILABLE,
            ci_state=CiState.FAILING,
        )
    )
    assert risk.score == 63
    assert risk.level == "high"
    assert confidence.score == 39
    assert confidence.level == "low"


def test_low_risk_low_confidence_remains_independent() -> None:
    risk = calculate_merge_risk([signal("future.informational", severity=SignalSeverity.INFO)])
    confidence = calculate_evidence_confidence(
        snapshot(
            [changed_file("unknown.one", patch=None)],
            files_complete=False,
            commits_complete=False,
            ci_visibility=CiVisibility.UNAVAILABLE,
            ci_state=CiState.UNKNOWN,
        )
    )
    assert risk.score == 0
    assert risk.level == "low"
    assert confidence.score == 29
    assert confidence.level == "low"


@pytest.mark.parametrize(
    ("visible", "total", "expected_points"),
    [(5, 5, 25), (4, 5, 20), (3, 5, 12), (2, 5, 5), (1, 5, 5), (0, 5, 0)],
)
def test_patch_visibility_thresholds(visible: int, total: int, expected_points: int) -> None:
    files = [
        changed_file(f"backend/app/file_{index}.py", patch="@@ -1 +1 @@\n+new" if index < visible else None)
        for index in range(total)
    ]
    component = next(component for component in calculate_evidence_confidence(snapshot(files)).components if component.id == "patch_visibility")
    assert component.awarded_points == expected_points


def test_patch_visibility_excludes_asset_and_binary_like_changes() -> None:
    assessment = calculate_evidence_confidence(snapshot([changed_file("assets/logo.png", patch=None), changed_file("dist/app.min.js", patch=None)]))
    patch_component = next(component for component in assessment.components if component.id == "patch_visibility")
    assert patch_component.status == "not_applicable"
    assert patch_component.awarded_points == 25


def test_ci_visibility_changes_confidence_but_ci_outcome_does_not() -> None:
    passing = calculate_evidence_confidence(snapshot([changed_file("backend/app/main.py")], ci_state=CiState.PASSING))
    failing = calculate_evidence_confidence(snapshot([changed_file("backend/app/main.py")], ci_state=CiState.FAILING))
    partial = calculate_evidence_confidence(snapshot([changed_file("backend/app/main.py")], ci_visibility=CiVisibility.PARTIAL))
    assert passing.score == failing.score
    assert partial.score == passing.score - 7


def test_classification_coverage_thresholds_and_warnings() -> None:
    assessment = calculate_evidence_confidence(
        snapshot(
            [
                changed_file("backend/app/main.py"),
                changed_file("unknown.one"),
                changed_file("unknown.two"),
                changed_file("unknown.three"),
            ]
        )
    )
    component = next(component for component in assessment.components if component.id == "classification_coverage")
    assert component.awarded_points == 2
    assert "Classification coverage is limited." in assessment.warnings
