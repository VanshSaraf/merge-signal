from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from app.domain.file_classification import (
    FileClassification,
    FileClassificationSummary,
    FileKind,
    FileLanguage,
)
from app.domain.review_signal import ReviewSignal, ReviewSignalSummary
from app.domain.readiness import (
    DecisionEffect,
    DecisionReason,
    MergeReadinessAssessment,
    MergeReadinessDecision,
)
from app.domain.scoring import (
    ConfidenceComponent,
    ConfidenceComponentStatus,
    EvidenceConfidenceAssessment,
    EvidenceConfidenceLevel,
    MergeRiskAssessment,
    MergeRiskLevel,
    RiskGroup,
    RiskGroupScore,
)


class StrictDomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PullRequestReference(StrictDomainModel):
    """Normalized identity for a public GitHub pull request."""

    owner: str = Field(description="GitHub repository owner or organization.")
    repository: str = Field(description="GitHub repository name.")
    pull_number: PositiveInt = Field(description="Positive GitHub pull-request number.")
    canonical_url: str = Field(description="Canonical public GitHub pull-request URL.")


class PullRequestAuthor(StrictDomainModel):
    login: str = Field(description="GitHub user login.")
    avatar_url: str | None = Field(description="GitHub avatar URL when available.")
    html_url: str | None = Field(description="GitHub profile URL when available.")


class PullRequestBranch(StrictDomainModel):
    ref: str = Field(description="Branch ref.")
    sha: str = Field(description="Branch commit SHA.")
    repository_full_name: str = Field(description="Repository full name for the branch.")


def unknown_file_classification() -> FileClassification:
    return FileClassification(
        primary_kind=FileKind.UNKNOWN,
        areas=[],
        language=FileLanguage.UNKNOWN,
        matches=[],
        warnings=["No explicit file-kind rule matched.", "No explicit language rule matched."],
    )


def empty_signal_summary() -> ReviewSignalSummary:
    return ReviewSignalSummary(
        total_signals=0,
        counts_by_severity=[],
        counts_by_category=[],
        files_with_signals=[],
        high_attention_files=[],
        patch_based_signal_count=0,
        metadata_signal_count=0,
        ci_signal_count=0,
        warnings=[],
        rules_version="v1",
    )


def empty_merge_risk_assessment() -> MergeRiskAssessment:
    return MergeRiskAssessment(
        score=0,
        level=MergeRiskLevel.LOW,
        max_score=100,
        group_scores=[
            RiskGroupScore(group=RiskGroup.CHANGE_SCOPE, raw_points=0, applied_points=0, cap=20, capped_points=0, contribution_count=0),
            RiskGroupScore(group=RiskGroup.SENSITIVE_SYSTEMS, raw_points=0, applied_points=0, cap=25, capped_points=0, contribution_count=0),
            RiskGroupScore(group=RiskGroup.TESTING, raw_points=0, applied_points=0, cap=15, capped_points=0, contribution_count=0),
            RiskGroupScore(group=RiskGroup.CI, raw_points=0, applied_points=0, cap=20, capped_points=0, contribution_count=0),
            RiskGroupScore(group=RiskGroup.OPERATIONAL_CHANGE, raw_points=0, applied_points=0, cap=15, capped_points=0, contribution_count=0),
            RiskGroupScore(group=RiskGroup.CODE_QUALITY, raw_points=0, applied_points=0, cap=5, capped_points=0, contribution_count=0),
        ],
        contributions=[],
        contributing_signal_count=0,
        non_scoring_signal_count=0,
        rules_version="v1",
        limitations=[
            "Merge risk is a deterministic heuristic, not a probability.",
            "Merge risk is not a merge decision and does not prove a pull request contains a defect.",
            "A low merge-risk score does not mean a pull request is safe.",
        ],
    )


def empty_evidence_confidence_assessment() -> EvidenceConfidenceAssessment:
    return EvidenceConfidenceAssessment(
        score=100,
        level=EvidenceConfidenceLevel.HIGH,
        max_score=100,
        components=[
            ConfidenceComponent(
                id="pull_request_metadata",
                name="Pull-request metadata",
                maximum_points=15,
                awarded_points=15,
                status=ConfidenceComponentStatus.COMPLETE,
                explanation="Core normalized pull-request metadata is present.",
                limitations=["Snapshot creation requires valid core metadata."],
            ),
            ConfidenceComponent(
                id="changed_file_collection",
                name="Changed-file collection",
                maximum_points=25,
                awarded_points=25,
                status=ConfidenceComponentStatus.COMPLETE,
                explanation="Changed-file collection completed.",
                limitations=[],
            ),
            ConfidenceComponent(
                id="patch_visibility",
                name="Patch visibility",
                maximum_points=25,
                awarded_points=25,
                status=ConfidenceComponentStatus.COMPLETE,
                explanation="Patch text is available for all patch-eligible files.",
                limitations=[],
            ),
            ConfidenceComponent(
                id="commit_collection",
                name="Commit collection",
                maximum_points=10,
                awarded_points=10,
                status=ConfidenceComponentStatus.COMPLETE,
                explanation="Commit collection completed.",
                limitations=[],
            ),
            ConfidenceComponent(
                id="ci_visibility",
                name="CI visibility",
                maximum_points=15,
                awarded_points=15,
                status=ConfidenceComponentStatus.COMPLETE,
                explanation="CI visibility is complete for observed check-run and commit-status surfaces.",
                limitations=[],
            ),
            ConfidenceComponent(
                id="classification_coverage",
                name="Classification coverage",
                maximum_points=10,
                awarded_points=10,
                status=ConfidenceComponentStatus.COMPLETE,
                explanation="Changed files have a known kind or language.",
                limitations=[],
            ),
        ],
        warnings=[],
        rules_version="v1",
        limitations=[
            "Evidence confidence measures visibility and completeness, not code quality.",
            "Complete observable data can still miss semantic or runtime issues.",
        ],
    )


def empty_merge_readiness_assessment() -> MergeReadinessAssessment:
    return MergeReadinessAssessment(
        decision=MergeReadinessDecision.READY,
        decisive_rule_id="readiness.ready_baseline",
        reasons=[
            DecisionReason(
                rule_id="readiness.ready_baseline",
                title="No readiness concerns observed",
                description="No blocking, resolution-required, or caution condition was observed in the available snapshot.",
                effect=DecisionEffect.CONTEXT,
                observed_value="no_readiness_concerns",
                related_signal_ids=[],
                affected_files=[],
                explanation="No blocking, resolution-required, or caution condition was observed in the available snapshot.",
                limitations=["Ready does not prove correctness or safety."],
            )
        ],
        blocking_reason_count=0,
        resolution_reason_count=0,
        caution_reason_count=0,
        context_reason_count=1,
        rules_version="v1",
        limitations=[
            "A readiness decision is a deterministic heuristic, not proof of correctness.",
            "Ready does not mean safe or bug-free.",
            "Human review remains necessary.",
            "Decisions use only the evidence available in the snapshot.",
        ],
    )


class PullRequestMetadata(StrictDomainModel):
    number: int = Field(description="Pull-request number.")
    title: str = Field(description="Pull-request title.")
    body: str | None = Field(description="Pull-request body.")
    state: str = Field(description="Pull-request state.")
    draft: bool = Field(description="Whether the pull request is a draft.")
    html_url: str = Field(description="GitHub pull-request URL.")
    author: PullRequestAuthor = Field(description="Pull-request author.")
    base_branch: PullRequestBranch = Field(description="Base branch.")
    head_branch: PullRequestBranch = Field(description="Head branch.")
    head_sha: str = Field(description="Head commit SHA.")
    created_at: datetime = Field(description="Creation timestamp.")
    updated_at: datetime = Field(description="Last update timestamp.")
    closed_at: datetime | None = Field(description="Close timestamp when available.")
    merged_at: datetime | None = Field(description="Merge timestamp when available.")
    additions: int = Field(description="Total additions reported by GitHub.")
    deletions: int = Field(description="Total deletions reported by GitHub.")
    changed_files: int = Field(description="Changed-file count reported by GitHub.")
    commit_count: int = Field(description="Commit count reported by GitHub.")
    mergeable: bool | None = Field(description="GitHub mergeable value when computed.")
    mergeable_state: str | None = Field(description="GitHub mergeable state when available.")
    labels: list[str] = Field(description="Pull-request label names.")


class ChangedFile(StrictDomainModel):
    filename: str = Field(description="Changed file path.")
    status: str = Field(description="GitHub file status.")
    additions: int = Field(description="Line additions.")
    deletions: int = Field(description="Line deletions.")
    changes: int = Field(description="Total line changes.")
    patch: str | None = Field(description="Patch text when GitHub provides it.")
    previous_filename: str | None = Field(description="Previous path for renamed files.")
    blob_url: str | None = Field(description="GitHub blob URL when available.")
    classification: FileClassification = Field(
        default_factory=unknown_file_classification,
        description="Deterministic classification of the current file path.",
    )
    previous_classification: FileClassification | None = Field(
        default=None,
        description="Deterministic classification of the previous file path for renamed files.",
    )


class PullRequestCommit(StrictDomainModel):
    sha: str = Field(description="Commit SHA.")
    message: str = Field(description="Commit message.")
    html_url: str | None = Field(description="GitHub commit URL when available.")
    author_login: str | None = Field(description="Linked GitHub author login when available.")
    author_name: str | None = Field(description="Commit author name when available.")
    authored_at: datetime | None = Field(description="Authored timestamp when available.")
    committed_at: datetime | None = Field(description="Committed timestamp when available.")


class GitHubRateLimit(StrictDomainModel):
    limit: int | None = Field(description="GitHub rate limit when available.")
    remaining: int | None = Field(description="Remaining GitHub requests when available.")
    used: int | None = Field(description="Used GitHub requests when available.")
    resource: str | None = Field(description="GitHub rate-limit resource when available.")
    reset_at: datetime | None = Field(description="Rate-limit reset time when available.")


class CiState(StrEnum):
    PASSING = "passing"
    FAILING = "failing"
    PENDING = "pending"
    MISSING = "missing"
    UNKNOWN = "unknown"


class CiVisibility(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class CheckRunRecord(StrictDomainModel):
    id: int = Field(description="GitHub check-run identifier.")
    name: str = Field(description="Check-run name.")
    status: str = Field(description="GitHub check-run status.")
    conclusion: str | None = Field(description="GitHub check-run conclusion when available.")
    provider_name: str | None = Field(description="Provider application name when available.")
    provider_slug: str | None = Field(description="Provider application slug when available.")
    details_url: str | None = Field(description="External details URL when available.")
    started_at: datetime | None = Field(description="Check-run start timestamp when available.")
    completed_at: datetime | None = Field(description="Check-run completion timestamp when available.")


class CommitStatusRecord(StrictDomainModel):
    id: int = Field(description="GitHub commit-status identifier.")
    context: str = Field(description="Commit-status context.")
    state: str = Field(description="GitHub commit-status state.")
    description: str | None = Field(description="Commit-status description when available.")
    target_url: str | None = Field(description="Target URL when available.")
    creator_login: str | None = Field(description="Status creator login when available.")
    created_at: datetime = Field(description="Creation timestamp.")
    updated_at: datetime = Field(description="Last update timestamp.")


class CiCompleteness(StrictDomainModel):
    check_runs_complete: bool = Field(description="Whether check-run retrieval completed.")
    commit_statuses_complete: bool = Field(description="Whether commit-status retrieval completed.")
    check_run_pages_fetched: int = Field(description="Check-run pages fetched.")
    commit_status_pages_fetched: int = Field(description="Commit-status pages fetched.")
    raw_status_record_count: int = Field(description="Raw status records observed before context reduction.")
    unique_status_context_count: int = Field(description="Unique current status contexts.")
    warnings: list[str] = Field(description="CI completeness warnings.")


class PullRequestCi(StrictDomainModel):
    state: CiState = Field(description="Aggregated observed CI state.")
    visibility: CiVisibility = Field(description="CI visibility completeness.")
    check_runs: list[CheckRunRecord] = Field(description="Normalized check runs.")
    commit_statuses: list[CommitStatusRecord] = Field(description="Current commit statuses by context.")
    total_check_runs: int = Field(description="Total check runs reported or observed.")
    total_status_contexts: int = Field(description="Unique current status contexts.")
    passing_count: int = Field(description="Current passing records.")
    failing_count: int = Field(description="Current failing records.")
    pending_count: int = Field(description="Current pending records.")
    neutral_count: int = Field(description="Current neutral check runs.")
    skipped_count: int = Field(description="Current skipped check runs.")
    warnings: list[str] = Field(description="CI warnings.")
    fetched_at: datetime = Field(description="UTC timestamp when CI data was fetched.")
    completeness: CiCompleteness = Field(description="CI completeness details.")
    rate_limit: GitHubRateLimit | None = Field(description="Latest CI rate-limit metadata when available.")


class SnapshotCompleteness(StrictDomainModel):
    files_complete: bool = Field(description="Whether changed-file retrieval is complete.")
    commits_complete: bool = Field(description="Whether commit retrieval is complete.")
    missing_patch_count: int = Field(description="Number of changed files without patches.")
    warnings: list[str] = Field(description="Completeness and partial-data warnings.")


class PullRequestSnapshot(StrictDomainModel):
    reference: PullRequestReference = Field(description="Normalized pull-request reference.")
    metadata: PullRequestMetadata = Field(description="Normalized pull-request metadata.")
    files: list[ChangedFile] = Field(description="Changed files in GitHub order.")
    commits: list[PullRequestCommit] = Field(description="Commits in GitHub order.")
    ci: PullRequestCi = Field(description="Read-only CI visibility for the pull-request head SHA.")
    classification_summary: FileClassificationSummary = Field(
        description="Pull-request-level summary of changed-file classifications."
    )
    signals: list[ReviewSignal] = Field(
        default_factory=list,
        description="Deterministic review signals observed from the snapshot data.",
    )
    signal_summary: ReviewSignalSummary = Field(
        default_factory=empty_signal_summary,
        description="Pull-request-level summary of review signals.",
    )
    merge_risk: MergeRiskAssessment = Field(
        default_factory=empty_merge_risk_assessment,
        description="Deterministic merge-risk assessment derived from observed review signals.",
    )
    evidence_confidence: EvidenceConfidenceAssessment = Field(
        default_factory=empty_evidence_confidence_assessment,
        description="Deterministic evidence-confidence assessment derived from snapshot visibility.",
    )
    merge_readiness: MergeReadinessAssessment = Field(
        default_factory=empty_merge_readiness_assessment,
        description="Deterministic merge-readiness decision derived from normalized snapshot assessments.",
    )
    completeness: SnapshotCompleteness = Field(description="Snapshot completeness details.")
    fetched_at: datetime = Field(description="UTC timestamp when snapshot was fetched.")
    rate_limit: GitHubRateLimit = Field(description="Latest available GitHub rate-limit metadata.")
