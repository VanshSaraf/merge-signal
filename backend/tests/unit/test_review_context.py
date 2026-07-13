from datetime import UTC, datetime, timedelta

from app.domain.pull_request import (
    ReviewCommentRecord,
    PullRequestReviewRecord,
    ReviewState,
)
from app.services.review_context import (
    build_review_context,
    normalize_review_state,
    safe_github_url,
    sanitize_review_body,
)

BASE_TIME = datetime(2026, 7, 13, 10, 0, tzinfo=UTC)


def review(
    id: int,
    reviewer: str,
    state: ReviewState | str,
    submitted_at: datetime | None,
    body: str | None = "Looks good.",
) -> PullRequestReviewRecord:
    return PullRequestReviewRecord(
        id=id,
        reviewer_login=reviewer,
        state=normalize_review_state(state) if isinstance(state, str) else state,
        submitted_at=submitted_at,
        body_excerpt=sanitize_review_body(body),
        html_url=safe_github_url(f"https://github.com/octocat/Hello-World/pull/42#pullrequestreview-{id}"),
        commit_sha="abc123",
    )


def comment(
    id: int,
    reviewer: str,
    body: str,
    *,
    created_at: datetime | None = None,
    in_reply_to_id: int | None = None,
    path: str = "backend/app/main.py",
    line: int | None = 12,
    html_url: str | None = None,
) -> ReviewCommentRecord:
    return ReviewCommentRecord(
        id=id,
        reviewer_login=reviewer,
        body_excerpt=sanitize_review_body(body) or "",
        created_at=created_at or BASE_TIME,
        updated_at=None,
        html_url=safe_github_url(html_url or f"https://github.com/octocat/Hello-World/pull/42#discussion_r{id}"),
        pull_request_review_id=100,
        in_reply_to_id=in_reply_to_id,
        path=path,
        line=line,
        start_line=None,
        side="RIGHT",
        start_side=None,
        commit_sha="abc123",
    )


def test_review_context_counts_states_and_latest_reviewer_state() -> None:
    context = build_review_context(
        [
            review(1, "alice", ReviewState.COMMENTED, BASE_TIME),
            review(2, "alice", ReviewState.APPROVED, BASE_TIME + timedelta(minutes=4)),
            review(3, "bob", ReviewState.CHANGES_REQUESTED, BASE_TIME + timedelta(minutes=2)),
            review(4, "carol", ReviewState.DISMISSED, BASE_TIME + timedelta(minutes=3)),
            review(5, "drew", ReviewState.PENDING, None),
        ],
        [],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=1,
        comment_pages_fetched=1,
    )

    assert context.review_count == 5
    assert context.approved_count == 1
    assert context.changes_requested_count == 1
    assert context.commented_count == 1
    assert context.dismissed_count == 1
    assert context.pending_count == 1
    assert {state.reviewer_login: state.state for state in context.latest_reviewer_states}["alice"] == ReviewState.APPROVED


def test_review_threads_group_roots_replies_orphans_and_independent_threads() -> None:
    context = build_review_context(
        [],
        [
            comment(10, "alice", "Root one", created_at=BASE_TIME, path="app/a.py", line=4),
            comment(11, "bob", "Reply one", created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=10, path="app/a.py"),
            comment(12, "carol", "Root two", created_at=BASE_TIME + timedelta(minutes=2), path="app/a.py", line=8),
            comment(13, "drew", "Missing root reply", created_at=BASE_TIME + timedelta(minutes=3), in_reply_to_id=999, path="app/b.py"),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
    )

    assert context.thread_count == 3
    assert context.threads[0].root_comment_id == 10
    assert [reply.id for reply in context.threads[0].replies] == [11]
    assert context.threads[1].root_comment_id == 12
    assert context.threads[2].is_orphan_reply is True
    assert context.warnings


def test_review_context_deduplicates_and_orders_comments() -> None:
    context = build_review_context(
        [review(1, "alice", "APPROVED", BASE_TIME), review(1, "alice", "APPROVED", BASE_TIME)],
        [
            comment(20, "alice", "Later", created_at=BASE_TIME + timedelta(minutes=1)),
            comment(19, "alice", "Earlier", created_at=BASE_TIME),
            comment(19, "alice", "Duplicate", created_at=BASE_TIME),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=1,
        comment_pages_fetched=1,
    )

    assert context.review_count == 1
    assert context.comment_count == 2
    assert [thread.root_comment_id for thread in context.threads] == [19, 20]


def test_comment_sanitization_redacts_controls_html_credentials_and_bounds_length() -> None:
    body = "<b>Do not render</b>\x00 password = hunter2 " + ("x" * 1200)
    cleaned = sanitize_review_body(body)

    assert cleaned is not None
    assert "<b>" not in cleaned
    assert "\x00" not in cleaned
    assert "hunter2" not in cleaned
    assert "password=[REDACTED]" in cleaned
    assert len(cleaned) <= 900


def test_safe_github_url_only_accepts_https_github_without_credentials() -> None:
    assert safe_github_url("https://github.com/octocat/Hello-World/pull/42") is not None
    assert safe_github_url("http://github.com/octocat/Hello-World/pull/42") is None
    assert safe_github_url("https://token@github.com/octocat/Hello-World/pull/42") is None
    assert safe_github_url("https://example.com/octocat/Hello-World/pull/42") is None


def test_partial_and_unavailable_visibility_are_exposed() -> None:
    partial = build_review_context(
        [review(1, "alice", ReviewState.APPROVED, BASE_TIME)],
        [],
        reviews_complete=True,
        comments_complete=False,
        review_pages_fetched=1,
        comment_pages_fetched=0,
        warnings=["Inline review comments could not be retrieved from GitHub."],
    )
    unavailable = build_review_context(
        [],
        [],
        reviews_complete=False,
        comments_complete=False,
        review_pages_fetched=0,
        comment_pages_fetched=0,
    )

    assert partial.visibility == "partial"
    assert unavailable.visibility == "unavailable"
