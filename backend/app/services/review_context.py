from collections import Counter
import re
from urllib.parse import urlparse

from app.domain.pull_request import (
    PullRequestReviewRecord,
    ReviewCommentRecord,
    ReviewContext,
    ReviewContextCompleteness,
    ReviewerLatestState,
    ReviewContextVisibility,
    ReviewState,
    ReviewThreadRecord,
)

BODY_EXCERPT_LIMIT = 900
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
HTML_TAG_PATTERN = re.compile(r"<[^>\n]{1,200}>")
CREDENTIAL_VALUE_PATTERN = re.compile(
    r"(?i)\b(password|passwd|secret|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|private[_-]?key|client[_-]?secret)\b\s*[:=]\s*([^\s,;]+)"
)

REVIEW_LIMITATIONS = [
    "Review context reports observable GitHub review state only.",
    "MergeSignal does not determine whether review concerns are resolved in this milestone.",
    "Approvals and change requests may be stale after later commits.",
    "Review comments do not automatically change merge risk or readiness.",
]


def build_review_context(
    reviews: list[PullRequestReviewRecord],
    comments: list[ReviewThreadRecord] | list[ReviewCommentRecord],
    *,
    reviews_complete: bool,
    comments_complete: bool,
    review_pages_fetched: int,
    comment_pages_fetched: int,
    warnings: list[str] | None = None,
) -> ReviewContext:
    comment_records = list(comments)  # type: ignore[arg-type]
    if comment_records and isinstance(comment_records[0], ReviewThreadRecord):
        raise TypeError("build_review_context expects normalized review comments, not threads")
    review_items = _dedupe_reviews(reviews)
    comments_items = _dedupe_comments(comment_records)  # type: ignore[arg-type]
    thread_result = build_review_threads(comments_items)
    all_warnings = [*(warnings or []), *thread_result.warnings]
    counts = Counter(review.state for review in review_items)

    if reviews_complete and comments_complete:
        visibility = ReviewContextVisibility.COMPLETE
    elif not reviews_complete and not comments_complete and not review_items and not comments_items:
        visibility = ReviewContextVisibility.UNAVAILABLE
    else:
        visibility = ReviewContextVisibility.PARTIAL

    completeness = ReviewContextCompleteness(
        reviews_complete=reviews_complete,
        comments_complete=comments_complete,
        review_pages_fetched=review_pages_fetched,
        comment_pages_fetched=comment_pages_fetched,
        warnings=all_warnings,
    )
    return ReviewContext(
        visibility=visibility,
        completeness=completeness,
        review_count=len(review_items),
        comment_count=len(comments_items),
        thread_count=len(thread_result.threads),
        approved_count=counts[ReviewState.APPROVED],
        changes_requested_count=counts[ReviewState.CHANGES_REQUESTED],
        commented_count=counts[ReviewState.COMMENTED],
        dismissed_count=counts[ReviewState.DISMISSED],
        pending_count=counts[ReviewState.PENDING],
        reviews=sorted(review_items, key=_review_sort_key),
        latest_reviewer_states=_latest_reviewer_states(review_items),
        threads=thread_result.threads,
        warnings=all_warnings,
        limitations=REVIEW_LIMITATIONS,
    )


class ThreadBuildResult:
    def __init__(self, threads: list[ReviewThreadRecord], warnings: list[str]) -> None:
        self.threads = threads
        self.warnings = warnings


def build_review_threads(comments: list[ReviewCommentRecord]) -> ThreadBuildResult:
    comments = sorted(_dedupe_comments(comments), key=_comment_sort_key)
    by_id = {comment.id: comment for comment in comments}
    root_comments = [comment for comment in comments if comment.in_reply_to_id is None]
    replies_by_root: dict[int, list[ReviewCommentRecord]] = {comment.id: [] for comment in root_comments}
    orphan_replies: list[ReviewCommentRecord] = []
    warnings: list[str] = []

    for comment in comments:
        if comment.in_reply_to_id is None:
            continue
        root = by_id.get(comment.in_reply_to_id)
        if root is None:
            orphan_replies.append(comment)
            continue
        root_id = root.id if root.in_reply_to_id is None else root.in_reply_to_id
        replies_by_root.setdefault(root_id, []).append(comment)

    threads = [_thread_from_root(root, replies_by_root.get(root.id, []), is_orphan=False) for root in root_comments]
    for reply in orphan_replies:
        warnings.append(f"Inline review reply {reply.id} referenced unavailable root comment {reply.in_reply_to_id}.")
        threads.append(_thread_from_root(reply, [], is_orphan=True))
    return ThreadBuildResult(sorted(threads, key=_thread_sort_key), warnings)


def sanitize_review_body(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = CONTROL_CHARACTER_PATTERN.sub(" ", value)
    cleaned = HTML_TAG_PATTERN.sub("", cleaned)
    cleaned = CREDENTIAL_VALUE_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if not cleaned:
        return None
    if len(cleaned) > BODY_EXCERPT_LIMIT:
        return cleaned[: BODY_EXCERPT_LIMIT - 1].rstrip() + "…"
    return cleaned


def safe_github_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return None
    if parsed.netloc.casefold() != "github.com":
        return None
    return value


def normalize_review_state(value: str | None) -> ReviewState:
    normalized = str(value or "").casefold()
    return {
        "approved": ReviewState.APPROVED,
        "changes_requested": ReviewState.CHANGES_REQUESTED,
        "commented": ReviewState.COMMENTED,
        "dismissed": ReviewState.DISMISSED,
        "pending": ReviewState.PENDING,
    }.get(normalized, ReviewState.UNKNOWN)


def _thread_from_root(root: ReviewCommentRecord, replies: list[ReviewCommentRecord], *, is_orphan: bool) -> ReviewThreadRecord:
    ordered_replies = sorted(replies, key=_comment_sort_key)
    participants = sorted({root.reviewer_login, *(reply.reviewer_login for reply in ordered_replies)}, key=str.casefold)
    return ReviewThreadRecord(
        id=f"review-thread-{root.id}",
        root_comment_id=root.id,
        path=getattr(root, "path", None),
        line=getattr(root, "line", None),
        start_line=getattr(root, "start_line", None),
        side=getattr(root, "side", None),
        start_side=getattr(root, "start_side", None),
        root_comment=root,
        replies=ordered_replies,
        participant_logins=participants,
        html_url=root.html_url,
        is_orphan_reply=is_orphan,
    )


def _latest_reviewer_states(reviews: list[PullRequestReviewRecord]) -> list[ReviewerLatestState]:
    latest: dict[str, PullRequestReviewRecord] = {}
    for review in sorted(reviews, key=_review_sort_key):
        latest[review.reviewer_login] = review
    return [
        ReviewerLatestState(
            reviewer_login=reviewer,
            state=review.state,
            review_id=review.id,
            submitted_at=review.submitted_at,
        )
        for reviewer, review in sorted(latest.items(), key=lambda item: item[0].casefold())
    ]


def _dedupe_reviews(reviews: list[PullRequestReviewRecord]) -> list[PullRequestReviewRecord]:
    by_id: dict[int, PullRequestReviewRecord] = {}
    for review in sorted(reviews, key=_review_sort_key):
        by_id.setdefault(review.id, review)
    return list(by_id.values())


def _dedupe_comments(comments: list[ReviewCommentRecord]) -> list[ReviewCommentRecord]:
    by_id: dict[int, ReviewCommentRecord] = {}
    for comment in sorted(comments, key=_comment_sort_key):
        by_id.setdefault(comment.id, comment)
    return list(by_id.values())


def _review_sort_key(review: PullRequestReviewRecord) -> tuple[str, int]:
    return ((review.submitted_at.isoformat() if review.submitted_at else ""), review.id)


def _comment_sort_key(comment: ReviewCommentRecord) -> tuple[str, int]:
    return (comment.created_at.isoformat(), comment.id)


def _thread_sort_key(thread: ReviewThreadRecord) -> tuple[str, int]:
    return (thread.root_comment.created_at.isoformat(), thread.root_comment_id)
