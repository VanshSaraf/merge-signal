from datetime import UTC, datetime, timedelta

from app.domain.pull_request import (
    ReviewCommentRecord,
    ReviewConcernAttentionState,
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
    current_position: int | None = 3,
    original_position: int | None = 3,
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
        current_position=current_position,
        original_position=original_position,
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


def test_awaiting_author_response_when_reviewer_root_has_no_author_reply() -> None:
    context = build_review_context(
        [],
        [comment(30, "reviewer", "Can you adjust this?")],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
        head_sha="abc123",
    )

    lifecycle = context.threads[0].lifecycle
    assert lifecycle.attention_state == ReviewConcernAttentionState.AWAITING_AUTHOR_RESPONSE
    assert lifecycle.needs_attention is True
    assert lifecycle.has_author_reply is False


def test_author_reply_and_author_claimed_addressed_are_distinct_with_boundaries() -> None:
    author_replied = build_review_context(
        [],
        [
            comment(40, "reviewer", "Please update this.", created_at=BASE_TIME),
            comment(41, "octocat", "I can look at this soon.", created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=40),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )
    claimed = build_review_context(
        [],
        [
            comment(42, "reviewer", "Please update this.", created_at=BASE_TIME),
            comment(43, "octocat", "Pushed a fix for this.", created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=42),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )
    false_positive = build_review_context(
        [],
        [
            comment(44, "reviewer", "Please update this.", created_at=BASE_TIME),
            comment(45, "octocat", "The prefix changed.", created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=44),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )

    assert author_replied.threads[0].lifecycle.attention_state == ReviewConcernAttentionState.AUTHOR_REPLIED
    assert author_replied.threads[0].lifecycle.needs_attention is False
    assert claimed.threads[0].lifecycle.attention_state == ReviewConcernAttentionState.AUTHOR_CLAIMED_ADDRESSED
    assert claimed.threads[0].lifecycle.verification_needed is True
    assert false_positive.threads[0].lifecycle.attention_state == ReviewConcernAttentionState.AUTHOR_REPLIED


def test_author_described_changes_requires_verification_without_claiming_resolution() -> None:
    context = build_review_context(
        [],
        [
            comment(46, "reviewer", "Can the status survive tab changes?", created_at=BASE_TIME),
            comment(47, "octocat", "The links now preserve the selected filter.", created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=46),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )

    lifecycle = context.threads[0].lifecycle
    assert lifecycle.attention_state == ReviewConcernAttentionState.AUTHOR_DESCRIBED_CHANGES
    assert lifecycle.verification_needed is True
    assert lifecycle.author_described_changes is True
    assert lifecycle.author_claimed_addressed is False
    assert lifecycle.summary == "Author described changes; reviewer verification is still needed."


def test_author_described_changes_avoids_common_false_positive_words() -> None:
    context = build_review_context(
        [],
        [
            comment(48, "reviewer", "Can you check this?", created_at=BASE_TIME),
            comment(49, "octocat", "The prefix changed upstream, I can look later.", created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=48),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )

    assert context.threads[0].lifecycle.attention_state == ReviewConcernAttentionState.AUTHOR_REPLIED


def test_author_described_changes_matches_bounded_review_reply_phrases() -> None:
    phrases = [
        "The project summary loader no longer runs on the Settings view.",
        "The project query no longer runs when mode is settings.",
        "The review loader now only runs on the Review tab.",
        "The metrics loader now runs only for review mode.",
        "The project link preserves the selected filter.",
        "The project edit link keeps the selected filter.",
        "Moved the query behind the review-mode branch.",
        "Removed the query from the settings view.",
        "Added the condition before loading project members.",
        "Changed the logic for review mode.",
        "Updated the links to include status.",
        "Adjusted the behavior for switching tabs.",
        "Implemented the change in the route.",
    ]

    for index, phrase in enumerate(phrases, start=100):
        context = build_review_context(
            [],
            [
                comment(index, "reviewer", "Please update this.", created_at=BASE_TIME),
                comment(index + 1000, "octocat", phrase, created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=index),
            ],
            reviews_complete=True,
            comments_complete=True,
            review_pages_fetched=0,
            comment_pages_fetched=1,
            pr_author_login="octocat",
        )

        assert context.threads[0].lifecycle.attention_state == ReviewConcernAttentionState.AUTHOR_DESCRIBED_CHANGES


def test_simple_author_acknowledgements_remain_author_replied() -> None:
    acknowledgements = ["thanks", "noted", "understood", "will check", "looking into it"]

    for index, phrase in enumerate(acknowledgements, start=200):
        context = build_review_context(
            [],
            [
                comment(index, "reviewer", "Please update this.", created_at=BASE_TIME),
                comment(index + 1000, "octocat", phrase, created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=index),
            ],
            reviews_complete=True,
            comments_complete=True,
            review_pages_fetched=0,
            comment_pages_fetched=1,
            pr_author_login="octocat",
        )

        assert context.threads[0].lifecycle.attention_state == ReviewConcernAttentionState.AUTHOR_REPLIED


def test_reviewer_follow_up_takes_priority_after_author_claim() -> None:
    context = build_review_context(
        [],
        [
            comment(50, "reviewer", "Please update this.", created_at=BASE_TIME),
            comment(51, "octocat", "Fixed.", created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=50),
            comment(52, "reviewer", "There is still one issue.", created_at=BASE_TIME + timedelta(minutes=2), in_reply_to_id=50),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )

    lifecycle = context.threads[0].lifecycle
    assert lifecycle.attention_state == ReviewConcernAttentionState.REVIEWER_FOLLOW_UP
    assert lifecycle.has_reviewer_follow_up is True
    assert lifecycle.author_claimed_addressed is False


def test_outdated_requires_reliable_position_metadata_and_author_root_is_informational() -> None:
    outdated = build_review_context(
        [],
        [comment(60, "reviewer", "Old position", current_position=None, original_position=7)],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )
    force_push_unknown = build_review_context(
        [],
        [comment(61, "reviewer", "No reliable outdated metadata", current_position=7, original_position=7)],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
        head_sha="new-head",
    )
    informational = build_review_context(
        [],
        [comment(62, "octocat", "Note to self")],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )

    assert outdated.threads[0].lifecycle.attention_state == ReviewConcernAttentionState.OUTDATED
    assert outdated.threads[0].lifecycle.needs_attention is False
    assert force_push_unknown.threads[0].lifecycle.attention_state == ReviewConcernAttentionState.AWAITING_AUTHOR_RESPONSE
    assert informational.threads[0].lifecycle.attention_state == ReviewConcernAttentionState.INFORMATIONAL


def test_latest_review_state_and_stale_approval_summary() -> None:
    context = build_review_context(
        [
            review(70, "reviewer", ReviewState.CHANGES_REQUESTED, BASE_TIME, body="Needs changes."),
            review(71, "reviewer", ReviewState.APPROVED, BASE_TIME + timedelta(minutes=2), body="Approved."),
            review(72, "alice", ReviewState.APPROVED, BASE_TIME + timedelta(minutes=3), body="Looks good."),
            review(73, "bob", ReviewState.CHANGES_REQUESTED, BASE_TIME + timedelta(minutes=4), body="Needs changes."),
        ],
        [comment(74, "bob", "Please fix this.")],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=1,
        comment_pages_fetched=1,
        pr_author_login="octocat",
        head_sha="different-head",
    )

    latest = {state.reviewer_login: state.state for state in context.latest_reviewer_states}
    assert latest["reviewer"] == ReviewState.APPROVED
    assert context.concern_summary.active_latest_change_request_count == 1
    assert context.concern_summary.potentially_stale_approval_count == 2
    assert context.threads[0].lifecycle.active_latest_change_request is True


def test_lifecycle_summary_counts_and_provenance_are_thread_scoped() -> None:
    context = build_review_context(
        [],
        [
            comment(80, "reviewer", "First", created_at=BASE_TIME),
            comment(81, "octocat", "Done.", created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=80),
            comment(82, "reviewer", "Second", created_at=BASE_TIME + timedelta(minutes=2)),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )

    assert context.concern_summary.author_claimed_addressed_count == 1
    assert context.concern_summary.awaiting_author_response_count == 1
    assert "2 review conversations need attention" in context.concern_summary.summary
    first_thread_comment_ids = {fact.comment_id for fact in context.threads[0].lifecycle.provenance if fact.comment_id}
    assert first_thread_comment_ids <= {80, 81}


def test_author_replied_summary_is_grammatical_without_punctuation_only_text() -> None:
    context = build_review_context(
        [],
        [
            comment(90, "reviewer", "Please check this.", created_at=BASE_TIME),
            comment(91, "octocat", "I can look at this soon.", created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=90),
            comment(92, "reviewer", "Please check this too.", created_at=BASE_TIME + timedelta(minutes=2)),
            comment(93, "octocat", "I can look at this too.", created_at=BASE_TIME + timedelta(minutes=3), in_reply_to_id=92),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )

    assert context.concern_summary.summary == "The author replied to 2 review conversations; reviewer confirmation is not visible."
    assert context.concern_summary.summary.strip(".")


def test_mixed_author_reply_and_described_change_summary_is_non_duplicative() -> None:
    context = build_review_context(
        [],
        [
            comment(300, "reviewer", "Please update this.", created_at=BASE_TIME),
            comment(301, "octocat", "I can look at this soon.", created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=300),
            comment(302, "reviewer", "Please preserve status.", created_at=BASE_TIME + timedelta(minutes=2)),
            comment(303, "octocat", "Updated the links to include status.", created_at=BASE_TIME + timedelta(minutes=3), in_reply_to_id=302),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )

    assert context.concern_summary.summary == "The author replied to 2 review conversations and described changes for 1 review conversation; reviewer confirmation is not visible."


def test_all_author_described_change_summary_keeps_verification_boundary() -> None:
    context = build_review_context(
        [],
        [
            comment(310, "reviewer", "Please update this.", created_at=BASE_TIME),
            comment(311, "octocat", "The project summary loader no longer runs on the Settings view.", created_at=BASE_TIME + timedelta(minutes=1), in_reply_to_id=310),
            comment(312, "reviewer", "Please preserve status.", created_at=BASE_TIME + timedelta(minutes=2)),
            comment(313, "octocat", "Updated the links to preserve the selected filter.", created_at=BASE_TIME + timedelta(minutes=3), in_reply_to_id=312),
        ],
        reviews_complete=True,
        comments_complete=True,
        review_pages_fetched=0,
        comment_pages_fetched=1,
        pr_author_login="octocat",
    )

    assert context.concern_summary.summary == "The author replied to 2 review conversations and described changes for both; reviewer confirmation is not visible."
