from datetime import UTC, datetime

from app.domain.pull_request import (
    ChangedFile,
    CheckRunRecord,
    CiCompleteness,
    CiState,
    CiVisibility,
    CommitStatusRecord,
    GitHubRateLimit,
    PullRequestAuthor,
    PullRequestBranch,
    PullRequestCi,
    PullRequestCommit,
    PullRequestMetadata,
    PullRequestReference,
    PullRequestReviewRecord,
    PullRequestSnapshot,
    ReviewCommentRecord,
    ReviewState,
    SnapshotCompleteness,
)
from app.domain.review_signal import EvidenceKind, ReviewSignal, SignalCategory, SignalEvidence, SignalScope, SignalSeverity
from app.file_priority import calculate_file_priorities
from app.readiness import calculate_merge_readiness
from app.review_actions import build_review_actions
from app.scoring import calculate_evidence_confidence, calculate_merge_risk
from app.services.ci_explanation import build_ci_explanation
from app.services.ci_state import aggregate_ci_state
from app.services.file_classifier import classify_changed_files
from app.services.review_briefing import build_review_briefing
from app.services.review_context import build_review_context, sanitize_review_body
from app.signals.engine import analyze_snapshot_signals

BASE_TIME = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)


def changed_file(filename: str, *, additions: int = 1, deletions: int = 1, patch: str | None = "@@ -1 +1 @@\n-old\n+new") -> ChangedFile:
    return ChangedFile(filename=filename, status="modified", additions=additions, deletions=deletions, changes=additions + deletions, patch=patch, previous_filename=None, blob_url=None)


def review_record(reviewer_login: str, state: ReviewState) -> PullRequestReviewRecord:
    return PullRequestReviewRecord(id=900, reviewer_login=reviewer_login, state=state, submitted_at=BASE_TIME, body_excerpt=None, html_url="https://github.com/sample-org/review-console/pull/42#pullrequestreview-900", commit_sha="head")


def review_comment(id: int, reviewer_login: str, body: str, *, path: str, in_reply_to_id: int | None = None, created_at: datetime = BASE_TIME, current_position: int | None = 3) -> ReviewCommentRecord:
    return ReviewCommentRecord(
        id=id,
        reviewer_login=reviewer_login,
        body_excerpt=sanitize_review_body(body) or "",
        created_at=created_at,
        updated_at=None,
        html_url=f"https://github.com/sample-org/review-console/pull/42#discussion_r{id}",
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


def high_signal(path: str, signal_id: str = "sig-high") -> ReviewSignal:
    return ReviewSignal(
        id=signal_id,
        rule_id="security.credential_like_literal_added",
        title="Credential-like literal pattern added",
        description="A high-severity security signal was observed.",
        category=SignalCategory.SECURITY,
        severity=SignalSeverity.HIGH,
        scope=SignalScope.FILE,
        affected_files=[path],
        evidence=[SignalEvidence(kind=EvidenceKind.METADATA, message="Sanitized fixture evidence.")],
        limitations=[],
        tags=["fixture"],
    )


def production_without_tests_signal(path: str) -> ReviewSignal:
    return ReviewSignal(
        id="testing.production_change_without_test_files",
        rule_id="testing.production_change_without_test_files",
        title="No test files were changed in this pull request",
        description="Production-relevant files changed and no current changed file is classified as a test.",
        category=SignalCategory.TESTING,
        severity=SignalSeverity.MEDIUM,
        scope=SignalScope.FILE_SET,
        affected_files=[path],
        evidence=[SignalEvidence(kind=EvidenceKind.METADATA, message="Fixture evidence.")],
        limitations=["This does not prove test coverage is absent."],
        tags=["testing"],
    )


def custom_high_signal(path: str, title: str = "Unusual deployment evidence observed") -> ReviewSignal:
    return ReviewSignal(
        id="custom.high.signal:fixture",
        rule_id="custom.high.signal",
        title=title,
        description="A generic high-severity fixture signal was observed.",
        category=SignalCategory.INFRASTRUCTURE,
        severity=SignalSeverity.HIGH,
        scope=SignalScope.FILE,
        affected_files=[path],
        evidence=[SignalEvidence(kind=EvidenceKind.METADATA, message="Fixture evidence.")],
        limitations=[],
        tags=["fixture"],
    )


def merge_conflict_signal(*, title: str = "GitHub reports a merge conflict condition") -> ReviewSignal:
    return ReviewSignal(
        id="metadata.merge_conflict_observed:fixture",
        rule_id="metadata.merge_conflict_observed",
        title=title,
        description="GitHub reports mergeability data consistent with a conflict condition.",
        category=SignalCategory.METADATA,
        severity=SignalSeverity.HIGH,
        scope=SignalScope.PULL_REQUEST,
        affected_files=[],
        evidence=[SignalEvidence(kind=EvidenceKind.METADATA, message="GitHub mergeability indicates a conflict condition.")],
        limitations=["GitHub mergeability may be temporarily unavailable or recomputed."],
        tags=["metadata", "mergeability"],
    )


def snapshot(files: list[ChangedFile], *, ci: PullRequestCi | None = None, review_context=None, signals: list[ReviewSignal] | None = None, files_complete: bool = True) -> PullRequestSnapshot:
    classified_files, classification_summary = classify_changed_files(files)
    ci = ci or passing_ci()
    base = PullRequestSnapshot(
        reference=PullRequestReference(owner="sample-org", repository="review-console", pull_number=42, canonical_url="https://github.com/sample-org/review-console/pull/42"),
        metadata=PullRequestMetadata(
            number=42,
            title="Briefing fixture",
            body="Fixture",
            state="open",
            draft=False,
            html_url="https://github.com/sample-org/review-console/pull/42",
            author=PullRequestAuthor(login="review-author", avatar_url=None, html_url=None),
            base_branch=PullRequestBranch(ref="main", sha="base", repository_full_name="sample-org/review-console"),
            head_branch=PullRequestBranch(ref="feature", sha="head", repository_full_name="sample-org/review-console"),
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
        commits=[PullRequestCommit(sha="head", message="Fixture", html_url=None, author_login=None, author_name=None, authored_at=BASE_TIME, committed_at=BASE_TIME)],
        ci=ci,
        ci_explanation=build_ci_explanation(ci),
        review_context=review_context if review_context is not None else build_review_context([], [], reviews_complete=True, comments_complete=True, review_pages_fetched=0, comment_pages_fetched=0, pr_author_login="review-author", head_sha="head"),
        classification_summary=classification_summary,
        signals=signals or [],
        completeness=SnapshotCompleteness(files_complete=files_complete, commits_complete=True, missing_patch_count=sum(1 for file in classified_files if file.patch is None), warnings=[] if files_complete else ["Changed-file collection was incomplete."]),
        fetched_at=BASE_TIME,
        rate_limit=GitHubRateLimit(limit=None, remaining=None, used=None, resource=None, reset_at=None),
    )
    if signals is None:
        signal_result = analyze_snapshot_signals(base)
        base = base.model_copy(update={"signals": signal_result.signals, "signal_summary": signal_result.summary})
    base = base.model_copy(update={"merge_risk": calculate_merge_risk(base.signals), "evidence_confidence": calculate_evidence_confidence(base)})
    base = base.model_copy(update={"merge_readiness": calculate_merge_readiness(base)})
    ranked_files, file_priority_summary = calculate_file_priorities(base)
    base = base.model_copy(update={"ranked_files": ranked_files, "file_priority_summary": file_priority_summary})
    review_actions, review_action_summary = build_review_actions(base)
    return base.model_copy(update={"review_actions": review_actions, "review_action_summary": review_action_summary, "review_briefing": build_review_briefing(base.model_copy(update={"review_actions": review_actions, "review_action_summary": review_action_summary}))})


def passing_ci() -> PullRequestCi:
    return PullRequestCi(
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
        completeness=CiCompleteness(check_runs_complete=True, commit_statuses_complete=True, check_run_pages_fetched=1, commit_status_pages_fetched=1, raw_status_record_count=0, unique_status_context_count=0, warnings=[]),
        rate_limit=None,
    )


def failing_vercel_ci() -> PullRequestCi:
    return aggregate_ci_state(
        [],
        [
            CommitStatusRecord(
                id=1,
                context="Vercel",
                state="failure",
                description="Authorization required to deploy.",
                target_url="https://vercel.com/git/authorize?repo=sample-org-review-console",
                creator_login="vercel[bot]",
                created_at=BASE_TIME,
                updated_at=BASE_TIME,
            )
        ],
        check_runs_complete=True,
        commit_statuses_complete=True,
        check_run_pages_fetched=1,
        commit_status_pages_fetched=1,
        total_check_runs=0,
    )


def two_failing_ci_surfaces() -> PullRequestCi:
    return aggregate_ci_state(
        [
            CheckRunRecord(
                id=7,
                name="Static checks",
                status="completed",
                conclusion="failure",
                provider_name="GitHub Actions",
                provider_slug="github-actions",
                details_url="https://github.com/sample-org/review-console/actions/runs/1/job/7",
                started_at=BASE_TIME,
                completed_at=BASE_TIME,
            )
        ],
        [
            CommitStatusRecord(
                id=1,
                context="Vercel",
                state="failure",
                description="Authorization required to deploy.",
                target_url="https://vercel.com/git/authorize?repo=sample-org-review-console",
                creator_login="vercel[bot]",
                created_at=BASE_TIME,
                updated_at=BASE_TIME,
            )
        ],
        check_runs_complete=True,
        commit_statuses_complete=True,
        check_run_pages_fetched=1,
        commit_status_pages_fetched=1,
        total_check_runs=1,
    )


def duplicate_github_actions_test_failures() -> PullRequestCi:
    return aggregate_ci_state(
        [
            CheckRunRecord(
                id=7,
                name="Unit tests",
                status="completed",
                conclusion="failure",
                provider_name="GitHub Actions",
                provider_slug="github-actions",
                details_url="https://github.com/sample-org/review-console/actions/runs/1/job/7",
                started_at=BASE_TIME,
                completed_at=BASE_TIME,
            ),
            CheckRunRecord(
                id=8,
                name="Integration tests",
                status="completed",
                conclusion="failure",
                provider_name="github actions",
                provider_slug="github-actions",
                details_url="https://github.com/sample-org/review-console/actions/runs/1/job/8",
                started_at=BASE_TIME,
                completed_at=BASE_TIME,
            ),
        ],
        [],
        check_runs_complete=True,
        commit_statuses_complete=True,
        check_run_pages_fetched=1,
        commit_status_pages_fetched=1,
        total_check_runs=2,
    )


def test_briefing_identifies_specific_blocking_ci_surface_and_safe_link() -> None:
    result = snapshot([changed_file("backend/app/main.py")], ci=failing_vercel_ci())
    briefing = result.review_briefing

    assert briefing.status == "blocked"
    assert briefing.headline == "Blocked by failed Vercel authorization/configuration check."
    assert briefing.primary_reason is not None
    assert briefing.primary_reason.url == "https://vercel.com/git/authorize?repo=sample-org-review-console"
    assert briefing.review_focus[0].title == "Inspect failed Vercel authorization/configuration check"
    assert any(id.startswith("ci:commit_status:vercel:authorization_or_configuration:vercel:") for id in briefing.provenance.ci_item_ids)
    assert result.merge_readiness.decision.value == "blocked"
    assert [item.title for item in briefing.review_focus].count("Inspect failed Vercel authorization/configuration check") == 1
    assert "CI reports a failing state" not in [item.title for item in briefing.review_focus]
    assert "Inspect failing CI" not in [step.title for step in briefing.recommended_steps]
    assert sum("CI" in item or "ci" in item.casefold() or "Vercel" in item for item in briefing.checklist) == 1


def test_distinct_ci_failures_remain_distinct_in_briefing() -> None:
    result = snapshot([changed_file("backend/app/main.py")], ci=two_failing_ci_surfaces())
    titles = [item.title for item in result.review_briefing.review_focus]

    assert "Inspect failed Vercel authorization/configuration check" in titles
    assert "Inspect failed GitHub Actions check" in titles


def test_equivalent_ci_blockers_collapse_and_preserve_provenance() -> None:
    result = snapshot([changed_file("backend/app/main.py")], ci=duplicate_github_actions_test_failures())
    briefing = result.review_briefing
    titles = [item.title for item in briefing.review_focus]
    steps = [step.title for step in briefing.recommended_steps]

    assert titles.count("Inspect failed GitHub Actions test check") == 1
    assert steps.count("Inspect failed GitHub Actions test check") == 1
    assert len([id for id in briefing.provenance.ci_item_ids if "github actions:test" in id]) == 2
    assert briefing.review_focus[0].description == "2 test checks require review while failing."
    assert result.merge_risk.score == calculate_merge_risk(result.signals).score
    assert result.merge_readiness.decision.value == "blocked"
    assert result.evidence_confidence.score == 100


def test_merge_conflict_briefing_and_readiness_preserve_github_casing_without_rewriting_data() -> None:
    result = snapshot([changed_file("backend/app/main.py")], signals=[merge_conflict_signal()])
    briefing = result.review_briefing
    reason = result.merge_readiness.reasons[0]

    assert briefing.headline == "Blocked because GitHub reports a merge conflict condition."
    assert reason.title == "GitHub reports a merge conflict condition"
    assert reason.explanation == "GitHub mergeability data reports a merge conflict condition."
    assert reason.related_signal_ids == ["metadata.merge_conflict_observed:fixture"]
    assert result.reference.repository == "review-console"
    assert result.reference.canonical_url == "https://github.com/sample-org/review-console/pull/42"
    assert result.merge_readiness.decision.value == "blocked"
    assert result.merge_risk.score == calculate_merge_risk(result.signals).score
    assert result.evidence_confidence.score == 100
    assert "gitHub" not in briefing.headline
    assert "Github" not in briefing.headline
    assert "GitHub reports a merge conflict condition" in [item.title for item in briefing.review_focus]
    assert "Resolve the reported merge conflict" in [step.title for step in briefing.recommended_steps]
    assert "[ ] Resolve the reported merge conflict" in briefing.checklist
    assert "[ ] GitHub reports a merge conflict condition" not in briefing.checklist


def test_briefing_recommended_steps_use_imperative_fallback_for_unknown_signal_titles() -> None:
    path = "src/features/settings/handler.py"
    result = snapshot([changed_file(path)], signals=[custom_high_signal(path)])
    briefing = result.review_briefing

    assert [item.title for item in briefing.review_focus] == ["Unusual deployment evidence observed"]
    assert briefing.recommended_steps[0].title == "Review unusual deployment evidence observed"
    assert briefing.checklist[0] == "[ ] Review unusual deployment evidence observed"


def test_briefing_uses_review_concerns_without_treating_author_claim_as_verified() -> None:
    path = "app/(secure)/admin/projects/[projectId]/page.tsx"
    review_context = build_review_context(
        [review_record("reviewer", ReviewState.COMMENTED)],
        [
            review_comment(901, "reviewer", "Please revise this.", path=path),
            review_comment(902, "review-author", "Fixed.", path=path, in_reply_to_id=901, created_at=BASE_TIME.replace(minute=1)),
            review_comment(903, "reviewer", "Outdated concern.", path="backend/old.py", current_position=None),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=1,
        comment_pages_fetched=1,
        pr_author_login="review-author",
        head_sha="head",
    )
    result = snapshot([changed_file(path, additions=220, deletions=159), changed_file("backend/old.py")], review_context=review_context)
    briefing = result.review_briefing

    assert any(item.title == "Verify the author's claimed fix" for item in briefing.review_focus)
    assert all("backend/old.py" not in item.affected_files for item in briefing.review_focus)
    assert "is verified" not in " ".join(item.description for item in briefing.review_focus).casefold()
    assert "review-thread-901" in briefing.provenance.review_thread_ids
    assert "review-thread-903" not in briefing.provenance.review_thread_ids


def test_author_described_change_produces_verification_step_without_resolution_claim() -> None:
    path = "app/(secure)/admin/projects/[projectId]/page.tsx"
    review_context = build_review_context(
        [review_record("reviewer", ReviewState.COMMENTED)],
        [
            review_comment(904, "reviewer", "Please preserve status while switching tabs.", path=path),
            review_comment(905, "review-author", "Both links now include the active status.", path=path, in_reply_to_id=904, created_at=BASE_TIME.replace(minute=1)),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=1,
        comment_pages_fetched=1,
        pr_author_login="review-author",
        head_sha="head",
    )
    result = snapshot([changed_file(path, additions=220, deletions=159)], review_context=review_context)
    briefing_text = " ".join([*(item.description for item in result.review_briefing.review_focus), *(step.description for step in result.review_briefing.recommended_steps)])

    assert any(step.title == "Verify the author response" for step in result.review_briefing.recommended_steps)
    assert "verified fix" not in briefing_text.casefold()
    assert "reviewer verification is still needed" in briefing_text.casefold()


def test_audited_pr_shape_deduplicates_ci_review_and_file_steps() -> None:
    path = "app/(secure)/admin/projects/[projectId]/page.tsx"
    review_context = build_review_context(
        [review_record("reviewer", ReviewState.COMMENTED)],
        [
            review_comment(8101, "reviewer-one", "The project summary loader also runs in settings mode.", path=path),
            review_comment(8102, "review-author", "The project summary loader no longer runs on the Settings view.", path=path, in_reply_to_id=8101, created_at=BASE_TIME.replace(minute=1)),
            review_comment(8103, "reviewer-one", "The navigation links drop the active project filter.", path=path, created_at=BASE_TIME.replace(minute=2)),
            review_comment(8104, "review-author", "Updated the links to preserve the selected filter.", path=path, in_reply_to_id=8103, created_at=BASE_TIME.replace(minute=3)),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=1,
        comment_pages_fetched=1,
        pr_author_login="review-author",
        head_sha="fixture-head-sha",
    )
    result = snapshot(
        [changed_file(path, additions=204, deletions=175)],
        ci=failing_vercel_ci(),
        review_context=review_context,
        signals=[production_without_tests_signal(path)],
    )
    briefing = result.review_briefing
    step_titles = [step.title for step in briefing.recommended_steps]
    checklist = "\n".join(briefing.checklist)

    assert result.merge_readiness.decision.value == "blocked"
    assert result.merge_risk.score == 7
    assert result.evidence_confidence.score == 100
    assert [item.title for item in briefing.review_focus] == [
        "Inspect failed Vercel authorization/configuration check",
        "Verify the author response",
    ]
    assert step_titles == [
        "Inspect failed Vercel authorization/configuration check",
        "Verify the author response",
        "Review production change test evidence",
        f"Review {path}",
    ]
    assert "Review highest-priority files" not in step_titles
    assert "Inspect failing CI" not in step_titles
    assert checklist.count("Vercel") == 1
    assert "Review highest-priority files" not in checklist
    assert len(briefing.checklist) <= 5
    file_step = next(step for step in briefing.recommended_steps if step.title == f"Review {path}")
    assert file_step.description == "Large admin route change with review conversations and no corresponding test-file change."


def test_briefing_limits_items_deduplicates_and_keeps_current_snapshot_provenance() -> None:
    files = [changed_file(f"backend/app/file_{index}.py", additions=100, deletions=20) for index in range(6)]
    signals = [high_signal(file.filename, f"sig-{index}") for index, file in enumerate(files)]
    result = snapshot(files, signals=signals, files_complete=False)
    briefing = result.review_briefing

    assert len(briefing.review_focus) <= 3
    assert len(briefing.priority_files) <= 3
    assert len(briefing.recommended_steps) <= 5
    assert len(briefing.checklist) <= 5
    assert set(briefing.provenance.file_paths) <= {file.filename for file in files}
    assert all("not-a-real-secret-fixture" not in item for item in briefing.checklist)


def test_ready_briefing_has_current_visible_evidence_headline() -> None:
    result = snapshot([changed_file("docs/readme.md")])
    briefing = result.review_briefing

    assert briefing.status == "ready"
    assert briefing.headline.startswith("Ready based on")
    assert briefing.primary_reason is not None
    assert briefing.primary_reason.source_ids == ["readiness.ready_baseline"]
