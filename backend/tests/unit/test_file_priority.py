from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.file_classification import ChangeMagnitude
from app.domain.file_priority import (
    FilePriorityCount,
    FilePriorityFactor,
    FilePriorityLevel,
    FilePrioritySummary,
)
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
    PullRequestReviewRecord,
    ReviewCommentRecord,
    ReviewState,
)
from app.domain.review_signal import (
    EvidenceKind,
    ReviewSignal,
    SignalCategory,
    SignalEvidence,
    SignalScope,
    SignalSeverity,
)
from app.file_priority import calculate_file_priorities
from app.file_priority.engine import level_for_file_priority
from app.file_priority.rules import (
    FACTOR_GROUP_CAPS,
    FILE_PRIORITY_RULES_VERSION,
    SIGNAL_PRIORITY_WEIGHT_BY_RULE_ID,
    SIGNAL_PRIORITY_WEIGHTS,
)
from app.services.file_classifier import classify_changed_files
from app.services.review_context import build_review_context, sanitize_review_body
from app.signals.rules import RULE_BY_ID

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


def signal(
    rule_id: str,
    *,
    signal_id: str | None = None,
    affected_files: list[str] | None = None,
    scope: SignalScope = SignalScope.FILE_SET,
    category: SignalCategory = SignalCategory.CHANGE_SCOPE,
    severity: SignalSeverity = SignalSeverity.MEDIUM,
) -> ReviewSignal:
    return ReviewSignal(
        id=signal_id or f"{rule_id}:fixture",
        rule_id=rule_id,
        title=f"Observed {rule_id}",
        description="Deterministic fixture signal.",
        category=category,
        severity=severity,
        scope=scope,
        affected_files=affected_files or [],
        evidence=[SignalEvidence(kind=EvidenceKind.METADATA, message="Fixture evidence.")],
        limitations=[],
        tags=["fixture"],
    )


def review_record(reviewer_login: str, state: ReviewState, *, id: int = 900) -> PullRequestReviewRecord:
    return PullRequestReviewRecord(
        id=id,
        reviewer_login=reviewer_login,
        state=state,
        submitted_at=BASE_TIME,
        body_excerpt=None,
        html_url=f"https://github.com/octocat/Hello-World/pull/42#pullrequestreview-{id}",
        commit_sha="head",
    )


def review_comment(
    id: int,
    reviewer_login: str,
    body: str,
    *,
    path: str,
    created_at: datetime = BASE_TIME,
    in_reply_to_id: int | None = None,
    current_position: int | None = 3,
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
        current_position=current_position,
        original_position=3,
        commit_sha="head",
    )


def snapshot(files: list[ChangedFile], *, signals: list[ReviewSignal] | None = None, review_context=None) -> PullRequestSnapshot:
    classified_files, classification_summary = classify_changed_files(files)
    payload = dict(
        reference=PullRequestReference(
            owner="octocat",
            repository="Hello-World",
            pull_number=42,
            canonical_url="https://github.com/octocat/Hello-World/pull/42",
        ),
        metadata=PullRequestMetadata(
            number=42,
            title="File priority fixture",
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
            state=CiState.PASSING,
            visibility=CiVisibility.COMPLETE,
            check_runs=[],
            commit_statuses=[],
            total_check_runs=0,
            total_status_contexts=0,
            passing_count=1,
            failing_count=0,
            pending_count=0,
            neutral_count=0,
            skipped_count=0,
            warnings=[],
            fetched_at=BASE_TIME,
            completeness=CiCompleteness(
                check_runs_complete=True,
                commit_statuses_complete=True,
                check_run_pages_fetched=1,
                commit_status_pages_fetched=1,
                raw_status_record_count=0,
                unique_status_context_count=0,
                warnings=[],
            ),
            rate_limit=None,
        ),
        classification_summary=classification_summary,
        signals=signals or [],
        completeness=SnapshotCompleteness(
            files_complete=True,
            commits_complete=True,
            missing_patch_count=sum(1 for file in classified_files if file.patch is None),
            warnings=[],
        ),
        fetched_at=BASE_TIME,
        rate_limit=GitHubRateLimit(limit=None, remaining=None, used=None, resource=None, reset_at=None),
    )
    if review_context is not None:
        payload["review_context"] = review_context
    return PullRequestSnapshot(**payload)


@pytest.mark.parametrize(
    ("score", "level"),
    [(0, "low"), (19, "low"), (20, "medium"), (39, "medium"), (40, "high"), (69, "high"), (70, "very_high"), (100, "very_high")],
)
def test_file_priority_level_boundaries(score: int, level: str) -> None:
    assert level_for_file_priority(score) == level


@pytest.mark.parametrize(
    ("changes", "magnitude"),
    [(0, ChangeMagnitude.TINY), (19, ChangeMagnitude.TINY), (20, ChangeMagnitude.SMALL), (99, ChangeMagnitude.SMALL), (100, ChangeMagnitude.MEDIUM), (299, ChangeMagnitude.MEDIUM), (300, ChangeMagnitude.LARGE), (999, ChangeMagnitude.LARGE), (1000, ChangeMagnitude.VERY_LARGE)],
)
def test_change_magnitude_thresholds_are_deterministic(changes: int, magnitude: ChangeMagnitude) -> None:
    ranked_files, _summary = calculate_file_priorities(
        snapshot([changed_file("backend/app/main.py", additions=changes, deletions=0, changes=changes)])
    )

    assert ranked_files[0].change_magnitude == magnitude


def test_file_priority_domain_validation_and_summary_consistency() -> None:
    assert [level.value for level in FilePriorityLevel] == ["low", "medium", "high", "very_high"]
    assert FilePriorityFactor(
        id="fixture",
        category="change_size",
        points=1,
        description="Fixture factor.",
        related_signal_ids=[],
        observed_value=None,
    ).model_dump()["points"] == 1
    with pytest.raises(ValidationError):
        FilePriorityFactor(id="bad", category="change_size", points=-1, description="Bad.", related_signal_ids=[], observed_value=None)
    with pytest.raises(ValidationError):
        FilePrioritySummary(
            total_files=2,
            counts_by_level=[FilePriorityCount(name="low", count=1)],
            highest_priority_files=[],
            files_with_signal_factors=0,
            files_with_limited_patch_visibility=0,
            rules_version="v1",
            limitations=[],
        )


def test_priority_registry_references_real_signal_rules_and_caps_total_100() -> None:
    assert FILE_PRIORITY_RULES_VERSION == "v1"
    assert sum(FACTOR_GROUP_CAPS.values()) >= 100
    assert len(SIGNAL_PRIORITY_WEIGHT_BY_RULE_ID) == len(SIGNAL_PRIORITY_WEIGHTS)
    for configured in SIGNAL_PRIORITY_WEIGHTS:
        assert configured.rule_id in RULE_BY_ID
        assert configured.points >= 0


def test_every_changed_file_is_ranked_and_zero_score_files_remain_present() -> None:
    ranked_files, summary = calculate_file_priorities(
        snapshot(
            [
                changed_file("docs/guide.md", additions=1, deletions=1),
                changed_file("docs/README.md", additions=1, deletions=0),
            ]
        )
    )

    assert [file.rank for file in ranked_files] == [1, 2]
    assert {file.path for file in ranked_files} == {"docs/guide.md", "docs/README.md"}
    assert all(file.score == 0 for file in ranked_files)
    assert summary.total_files == 2
    assert summary.counts_by_level == [FilePriorityCount(name="low", count=2)]


def test_nextjs_context_and_review_concerns_lift_large_admin_route_out_of_low_priority() -> None:
    path = "app/(protected)/admin/cohort/[id]/page.tsx"
    review_context = build_review_context(
        [review_record("reviewer", ReviewState.CHANGES_REQUESTED)],
        [
            review_comment(901, "reviewer", "Please fix the cohort transition.", path=path),
            review_comment(902, "octocat", "Fixed.", path=path, created_at=BASE_TIME.replace(minute=1), in_reply_to_id=901),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=1,
        comment_pages_fetched=1,
        pr_author_login="octocat",
        head_sha="head",
    )
    signals = [signal("testing.sensitive_change_without_test_files", affected_files=[path])]
    ranked_files, _summary = calculate_file_priorities(
        snapshot([changed_file(path, additions=220, deletions=159, changes=379)], signals=signals, review_context=review_context)
    )
    file = ranked_files[0]
    factor_ids = {factor.id for factor in file.factors}

    assert file.language.value == "typescript"
    assert file.context.framework == "nextjs_app_router"
    assert file.context.component_role == "route_page"
    assert "admin" in file.context.areas
    assert "protected_route_group" in file.context.access_context
    assert file.context.domains == ["cohort"]
    assert file.context.is_dynamic_route is True
    assert file.change_magnitude == ChangeMagnitude.LARGE
    assert file.level in {FilePriorityLevel.HIGH, FilePriorityLevel.VERY_HIGH}
    assert "review_attention.active_change_request" in factor_ids
    assert "review_attention.author_claimed_addressed" in factor_ids
    assert "context.admin_surface" in factor_ids
    assert "context.dynamic_route" in factor_ids
    assert "signal.testing.sensitive_change_without_test_files" in factor_ids
    assert file.score == sum(factor.points for factor in file.factors)


def test_outdated_review_concern_does_not_inflate_file_priority_and_global_ci_is_ignored() -> None:
    path = "backend/app/main.py"
    review_context = build_review_context(
        [review_record("reviewer", ReviewState.COMMENTED)],
        [review_comment(901, "reviewer", "Old line.", path=path, current_position=None)],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=1,
        comment_pages_fetched=1,
        pr_author_login="octocat",
        head_sha="head",
    )
    signals = [signal("ci.failing", affected_files=[], scope=SignalScope.CI_SURFACE, category=SignalCategory.CI)]
    ranked_files, _summary = calculate_file_priorities(
        snapshot([changed_file(path), changed_file("docs/readme.md")], signals=signals, review_context=review_context)
    )
    by_path = {file.path: file for file in ranked_files}

    assert not any(factor.category == "review_attention" for factor in by_path[path].factors)
    assert by_path[path].related_signal_ids == []
    assert by_path["docs/readme.md"].related_signal_ids == []


def test_signal_factors_apply_only_to_explicit_current_file_paths() -> None:
    signals = [
        signal("security.credential_like_literal_added", signal_id="sig-1", affected_files=["backend/app/auth/session.py"]),
        signal("security.credential_like_literal_added", signal_id="sig-2", affected_files=["backend/app/auth/session.py"]),
        signal("ci.failing", signal_id="ci-pr-level", affected_files=[], scope=SignalScope.CI_SURFACE, category=SignalCategory.CI),
        signal("unknown.future_rule", signal_id="unknown", affected_files=["backend/app/auth/session.py"]),
    ]
    ranked_files, summary = calculate_file_priorities(
        snapshot(
            [
                changed_file("backend/app/auth/session.py"),
                changed_file("backend/app/auth/other.py"),
            ],
            signals=signals,
        )
    )
    by_path = {file.path: file for file in ranked_files}

    assert by_path["backend/app/auth/session.py"].related_signal_ids == ["sig-1", "sig-2", "unknown"]
    assert [factor.id for factor in by_path["backend/app/auth/session.py"].factors if factor.category == "signal_impact"] == [
        "signal.security.credential_like_literal_added"
    ]
    assert by_path["backend/app/auth/other.py"].related_signal_ids == []
    assert summary.files_with_signal_factors == 1


def test_file_specific_signal_association_includes_non_weighted_related_signals() -> None:
    path = "app/(protected)/admin/cohort/[id]/page.tsx"
    signals = [signal("testing.production_change_without_test_files", signal_id="sig-tests", affected_files=[path], category=SignalCategory.TESTING)]
    ranked_files, _summary = calculate_file_priorities(
        snapshot([changed_file(path, additions=204, deletions=175, changes=379)], signals=signals)
    )

    assert ranked_files[0].related_signal_ids == ["sig-tests"]


def test_renamed_file_signal_association_supports_previous_path_without_basename_fallback() -> None:
    signals = [
        signal("security.credential_like_literal_added", signal_id="sig-previous", affected_files=["old/auth/session.py"], category=SignalCategory.SECURITY),
        signal("security.credential_like_literal_added", signal_id="sig-basename", affected_files=["other/session.py"], category=SignalCategory.SECURITY),
    ]
    ranked_files, _summary = calculate_file_priorities(
        snapshot(
            [
                changed_file("backend/app/auth/session.py", status="renamed", previous_filename="old/auth/session.py"),
                changed_file("backend/app/auth/other.py"),
            ],
            signals=signals,
        )
    )
    by_path = {file.path: file for file in ranked_files}

    assert by_path["backend/app/auth/session.py"].related_signal_ids == ["sig-previous"]
    assert by_path["backend/app/auth/other.py"].related_signal_ids == []


def test_group_caps_and_total_cap_are_enforced_deterministically() -> None:
    signals = [
        signal("security.credential_like_literal_added", affected_files=["backend/app/auth/session.py"]),
        signal("security.security_control_disabled_hint", affected_files=["backend/app/auth/session.py"]),
        signal("database.destructive_migration_hint", affected_files=["backend/app/auth/session.py"]),
    ]

    ranked_files, _summary = calculate_file_priorities(
        snapshot(
            [
                changed_file(
                    "backend/app/auth/session.py",
                    status="renamed",
                    additions=800,
                    deletions=400,
                    changes=1200,
                    patch=None,
                    previous_filename="docs/session.py",
                ),
            ],
            signals=signals,
        )
    )
    file = ranked_files[0]
    totals = {
        category: sum(factor.points for factor in file.factors if factor.category == category)
        for category in FACTOR_GROUP_CAPS
    }

    assert file.score == 100
    assert totals["signal_impact"] == 50
    assert totals["sensitive_area"] == 25
    assert totals["change_size"] == 15
    assert totals["visibility"] == 5
    assert all(points <= FACTOR_GROUP_CAPS[category] for category, points in totals.items())


def test_visibility_rules_do_not_penalize_assets_for_missing_patch() -> None:
    ranked_files, summary = calculate_file_priorities(
        snapshot(
            [
                changed_file("assets/logo.png", patch=None),
                changed_file("dist/generated.pb.py", patch=None),
                changed_file("target/app.jar", patch=None),
            ]
        )
    )
    by_path = {file.path: file for file in ranked_files}

    assert not any(factor.category == "visibility" for factor in by_path["assets/logo.png"].factors)
    assert any(factor.category == "visibility" for factor in by_path["dist/generated.pb.py"].factors)
    assert any(factor.category == "visibility" for factor in by_path["target/app.jar"].factors)
    assert summary.files_with_limited_patch_visibility == 2


def test_rename_transition_and_ordering_are_stable() -> None:
    files = [
        changed_file("docs/z.md", additions=20, deletions=20),
        changed_file("backend/app/auth/roles.py", status="renamed", previous_filename="tests/test_roles.py"),
        changed_file("backend/app/api/routes.py", additions=100, deletions=100),
    ]
    ranked_files, summary = calculate_file_priorities(snapshot(list(reversed(files))))

    assert [file.rank for file in ranked_files] == [1, 2, 3]
    assert [file.path for file in ranked_files] == [
        "backend/app/auth/roles.py",
        "backend/app/api/routes.py",
        "docs/z.md",
    ]
    rename_factors = [factor.id for factor in ranked_files[0].factors if factor.category == "rename_transition"]
    assert rename_factors == ["rename_transition.moved_into_sensitive_area"]
    assert summary.highest_priority_files == [file.path for file in ranked_files]
