from collections import Counter
import re
from urllib.parse import urlparse

from app.domain.pull_request import (
    PullRequestReviewRecord,
    ReviewConcernAttentionState,
    ReviewConcernProvenance,
    ReviewConcernSummary,
    ReviewCommentRecord,
    ReviewContext,
    ReviewContextCompleteness,
    ReviewerLatestState,
    ReviewContextVisibility,
    ReviewState,
    ReviewThreadRecord,
    ReviewThreadLifecycle,
    ResolutionVisibility,
)

BODY_EXCERPT_LIMIT = 900
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
HTML_TAG_PATTERN = re.compile(r"<[^>\n]{1,200}>")
CREDENTIAL_VALUE_PATTERN = re.compile(
    r"(?i)\b(password|passwd|secret|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|private[_-]?key|client[_-]?secret)\b\s*[:=]\s*([^\s,;]+)"
)
AUTHOR_ADDRESSED_PATTERN = re.compile(
    r"(?i)(\bfixed\b|\baddressed\b|\bupdated\b|\bresolved\b|\bdone\b|\bpushed\s+a\s+fix\b|\bhandled\s+this\b|\bchanged\s+this\b)"
)
AUTHOR_DESCRIBED_CHANGES_PATTERN = re.compile(
    r"(?i)(\bchanged\s+(this|it|the|to|from)\b|\bmoved\b|\bremoved\b|\badded\b|\bupdated\b|\bimplemented\b|\badjusted\b|\bnow\s+includes?\b|\bnow\s+preserves?\b|\bnow\s+only\s+runs\b|\bno\s+longer\s+runs\b)"
)

REVIEW_LIMITATIONS = [
    "Review context reports observable GitHub review state only.",
    "MergeSignal does not determine whether review concerns are formally resolved in this milestone.",
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
    pr_author_login: str | None = None,
    head_sha: str | None = None,
    warnings: list[str] | None = None,
) -> ReviewContext:
    comment_records = list(comments)  # type: ignore[arg-type]
    if comment_records and isinstance(comment_records[0], ReviewThreadRecord):
        raise TypeError("build_review_context expects normalized review comments, not threads")
    review_items = _dedupe_reviews(reviews)
    comments_items = _dedupe_comments(comment_records)  # type: ignore[arg-type]
    latest_states = _latest_reviewer_states(review_items)
    thread_result = build_review_threads(
        comments_items,
        pr_author_login=pr_author_login,
        latest_reviewer_states=latest_states,
        reviews_by_id={review.id: review for review in review_items},
        head_sha=head_sha,
    )
    all_warnings = [*(warnings or []), *thread_result.warnings]
    counts = Counter(review.state for review in review_items)
    concern_summary = _build_concern_summary(thread_result.threads, latest_states, {review.id: review for review in review_items}, head_sha)

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
        concern_summary=concern_summary,
        reviews=sorted(review_items, key=_review_sort_key),
        latest_reviewer_states=latest_states,
        threads=thread_result.threads,
        warnings=all_warnings,
        limitations=REVIEW_LIMITATIONS,
    )


class ThreadBuildResult:
    def __init__(self, threads: list[ReviewThreadRecord], warnings: list[str]) -> None:
        self.threads = threads
        self.warnings = warnings


def build_review_threads(
    comments: list[ReviewCommentRecord],
    *,
    pr_author_login: str | None = None,
    latest_reviewer_states: list[ReviewerLatestState] | None = None,
    reviews_by_id: dict[int, PullRequestReviewRecord] | None = None,
    head_sha: str | None = None,
) -> ThreadBuildResult:
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

    threads = [
        _thread_from_root(
            root,
            replies_by_root.get(root.id, []),
            is_orphan=False,
            pr_author_login=pr_author_login,
            latest_reviewer_states=latest_reviewer_states or [],
            reviews_by_id=reviews_by_id or {},
            head_sha=head_sha,
        )
        for root in root_comments
    ]
    for reply in orphan_replies:
        warnings.append(f"Inline review reply {reply.id} referenced unavailable root comment {reply.in_reply_to_id}.")
        threads.append(
            _thread_from_root(
                reply,
                [],
                is_orphan=True,
                pr_author_login=pr_author_login,
                latest_reviewer_states=latest_reviewer_states or [],
                reviews_by_id=reviews_by_id or {},
                head_sha=head_sha,
            )
        )
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


def _thread_from_root(
    root: ReviewCommentRecord,
    replies: list[ReviewCommentRecord],
    *,
    is_orphan: bool,
    pr_author_login: str | None,
    latest_reviewer_states: list[ReviewerLatestState],
    reviews_by_id: dict[int, PullRequestReviewRecord],
    head_sha: str | None,
) -> ReviewThreadRecord:
    ordered_replies = sorted(replies, key=_comment_sort_key)
    participants = sorted({root.reviewer_login, *(reply.reviewer_login for reply in ordered_replies)}, key=str.casefold)
    lifecycle = _derive_thread_lifecycle(
        root,
        ordered_replies,
        is_orphan=is_orphan,
        pr_author_login=pr_author_login,
        latest_reviewer_states=latest_reviewer_states,
        reviews_by_id=reviews_by_id,
        head_sha=head_sha,
    )
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
        lifecycle=lifecycle,
    )


def _derive_thread_lifecycle(
    root: ReviewCommentRecord,
    replies: list[ReviewCommentRecord],
    *,
    is_orphan: bool,
    pr_author_login: str | None,
    latest_reviewer_states: list[ReviewerLatestState],
    reviews_by_id: dict[int, PullRequestReviewRecord],
    head_sha: str | None,
) -> ReviewThreadLifecycle:
    author_login = (pr_author_login or "").casefold()
    root_is_author = bool(author_login and root.reviewer_login.casefold() == author_login)
    author_replies = [
        reply
        for reply in replies
        if author_login and reply.reviewer_login.casefold() == author_login and reply.created_at > root.created_at
    ]
    latest_author_reply = max(author_replies, key=_comment_sort_key) if author_replies else None
    reviewer_follow_up = None
    if latest_author_reply is not None:
        reviewer_follow_up = next(
            (
                reply
                for reply in sorted(replies, key=_comment_sort_key)
                if reply.created_at > latest_author_reply.created_at
                and (not author_login or reply.reviewer_login.casefold() != author_login)
            ),
            None,
        )
    claimed_reply = next((reply for reply in reversed(author_replies) if AUTHOR_ADDRESSED_PATTERN.search(reply.body_excerpt)), None)
    described_reply = next((reply for reply in reversed(author_replies) if AUTHOR_DESCRIBED_CHANGES_PATTERN.search(reply.body_excerpt)), None)
    is_outdated = root.current_position is None and root.original_position is not None
    latest_state = next((state for state in latest_reviewer_states if state.reviewer_login == root.reviewer_login), None)
    active_change_request = latest_state is not None and latest_state.state == ReviewState.CHANGES_REQUESTED
    review = reviews_by_id.get(root.pull_request_review_id or -1)
    approval_validity = _approval_validity(latest_reviewer_states, reviews_by_id, head_sha)
    provenance = _base_provenance(root, pr_author_login, head_sha)

    if is_outdated:
        state = ReviewConcernAttentionState.OUTDATED
        needs_attention = False
        summary = "GitHub position metadata indicates this conversation is outdated."
        provenance.append(_provenance("position", root, "Root comment has original position metadata but no current position."))
    elif root_is_author:
        state = ReviewConcernAttentionState.INFORMATIONAL
        needs_attention = False
        summary = "The PR author opened this conversation, so MergeSignal treats it as informational."
    elif is_orphan:
        state = ReviewConcernAttentionState.UNKNOWN
        needs_attention = True
        summary = "The reply's root comment was not available, so attention cannot be safely dismissed."
    elif reviewer_follow_up is not None:
        state = ReviewConcernAttentionState.REVIEWER_FOLLOW_UP
        needs_attention = True
        summary = "A non-author participant replied after the latest author response."
        provenance.append(_provenance("reviewer_follow_up", reviewer_follow_up, "Reviewer or non-author participant commented after the latest author reply."))
    elif claimed_reply is not None:
        state = ReviewConcernAttentionState.AUTHOR_CLAIMED_ADDRESSED
        needs_attention = True
        summary = "The author claims this concern was addressed; reviewer confirmation is not visible."
        provenance.append(_provenance("author_claim", claimed_reply, "Author reply matched bounded addressed-claim language."))
    elif described_reply is not None:
        state = ReviewConcernAttentionState.AUTHOR_DESCRIBED_CHANGES
        needs_attention = True
        summary = "Author described changes; reviewer verification is still needed."
        provenance.append(_provenance("author_described_changes", described_reply, "Author reply matched bounded change-description language."))
    elif latest_author_reply is not None:
        state = ReviewConcernAttentionState.AUTHOR_REPLIED
        needs_attention = active_change_request
        summary = "The author replied, and no later reviewer follow-up is visible."
        provenance.append(_provenance("author_reply", latest_author_reply, "PR author replied after the root comment."))
    elif not root_is_author:
        state = ReviewConcernAttentionState.AWAITING_AUTHOR_RESPONSE
        needs_attention = True
        summary = "The root comment was made by a non-author participant and no later author reply is visible."
    else:
        state = ReviewConcernAttentionState.UNKNOWN
        needs_attention = True
        summary = "Available evidence does not support a more specific lifecycle state."

    if active_change_request:
        provenance.append(
            ReviewConcernProvenance(
                source="latest_review_state",
                comment_id=None,
                review_id=latest_state.review_id if latest_state else None,
                actor_login=root.reviewer_login,
                observed_at=latest_state.submitted_at if latest_state else None,
                detail="Root reviewer latest observable review state requests changes.",
            )
        )
    if review and review.commit_sha and head_sha and review.commit_sha != head_sha:
        provenance.append(
            ReviewConcernProvenance(
                source="review_commit",
                comment_id=None,
                review_id=review.id,
                actor_login=review.reviewer_login,
                observed_at=review.submitted_at,
                detail="Review commit SHA differs from the current PR head SHA.",
            )
        )

    return ReviewThreadLifecycle(
        attention_state=state,
        needs_attention=needs_attention,
        verification_needed=state in {ReviewConcernAttentionState.AUTHOR_CLAIMED_ADDRESSED, ReviewConcernAttentionState.AUTHOR_DESCRIBED_CHANGES},
        has_author_reply=bool(author_replies),
        has_reviewer_follow_up=reviewer_follow_up is not None,
        author_claimed_addressed=claimed_reply is not None and reviewer_follow_up is None,
        author_described_changes=described_reply is not None and claimed_reply is None and reviewer_follow_up is None,
        is_outdated=is_outdated,
        resolution_visibility=ResolutionVisibility.UNAVAILABLE,
        active_latest_change_request=active_change_request,
        approval_validity=approval_validity,
        summary=summary,
        provenance=provenance,
        limitations=["MergeSignal cannot verify that the code change resolves this concern."],
    )


def _base_provenance(root: ReviewCommentRecord, pr_author_login: str | None, head_sha: str | None) -> list[ReviewConcernProvenance]:
    facts = [
        _provenance("root_comment", root, "Root inline review comment for this conversation."),
    ]
    if pr_author_login:
        facts.append(
            ReviewConcernProvenance(
                source="pr_author",
                comment_id=None,
                review_id=None,
                actor_login=pr_author_login,
                observed_at=None,
                detail="PR author login used for author-reply matching.",
            )
        )
    if head_sha:
        facts.append(
            ReviewConcernProvenance(
                source="head_sha",
                comment_id=None,
                review_id=None,
                actor_login=None,
                observed_at=None,
                detail="Current PR head SHA used for commit mismatch checks.",
            )
        )
    return facts


def _provenance(source: str, comment: ReviewCommentRecord, detail: str) -> ReviewConcernProvenance:
    return ReviewConcernProvenance(
        source=source,
        comment_id=comment.id,
        review_id=comment.pull_request_review_id,
        actor_login=comment.reviewer_login,
        observed_at=comment.created_at,
        detail=detail,
    )


def _approval_validity(
    latest_reviewer_states: list[ReviewerLatestState],
    reviews_by_id: dict[int, PullRequestReviewRecord],
    head_sha: str | None,
) -> str:
    if not head_sha:
        return "unknown"
    stale = [
        reviews_by_id.get(state.review_id)
        for state in latest_reviewer_states
        if state.state == ReviewState.APPROVED
    ]
    if any(review and review.commit_sha and review.commit_sha != head_sha for review in stale):
        return "potentially_stale"
    return "unknown"


def _build_concern_summary(
    threads: list[ReviewThreadRecord],
    latest_states: list[ReviewerLatestState],
    reviews_by_id: dict[int, PullRequestReviewRecord],
    head_sha: str | None,
) -> ReviewConcernSummary:
    state_counts = Counter(thread.lifecycle.attention_state for thread in threads)
    needing_attention = sum(1 for thread in threads if thread.lifecycle.needs_attention)
    active_change_requests = sum(1 for state in latest_states if state.state == ReviewState.CHANGES_REQUESTED)
    potentially_stale_approvals = sum(
        1
        for state in latest_states
        if state.state == ReviewState.APPROVED
        and head_sha
        and (review := reviews_by_id.get(state.review_id)) is not None
        and review.commit_sha is not None
        and review.commit_sha != head_sha
    )
    return ReviewConcernSummary(
        total_conversations=len(threads),
        needing_attention_count=needing_attention,
        awaiting_author_response_count=state_counts[ReviewConcernAttentionState.AWAITING_AUTHOR_RESPONSE],
        author_replied_count=state_counts[ReviewConcernAttentionState.AUTHOR_REPLIED],
        author_described_changes_count=state_counts[ReviewConcernAttentionState.AUTHOR_DESCRIBED_CHANGES],
        author_claimed_addressed_count=state_counts[ReviewConcernAttentionState.AUTHOR_CLAIMED_ADDRESSED],
        reviewer_follow_up_count=state_counts[ReviewConcernAttentionState.REVIEWER_FOLLOW_UP],
        outdated_count=state_counts[ReviewConcernAttentionState.OUTDATED],
        informational_count=state_counts[ReviewConcernAttentionState.INFORMATIONAL],
        unknown_count=state_counts[ReviewConcernAttentionState.UNKNOWN],
        active_latest_change_request_count=active_change_requests,
        potentially_stale_approval_count=potentially_stale_approvals,
        summary=_concern_summary_text(needing_attention, state_counts, active_change_requests),
    )


def _concern_summary_text(
    needing_attention: int,
    state_counts: Counter,
    active_change_requests: int,
) -> str:
    total = sum(state_counts.values())
    if not total:
        return "No inline review conversations were observed."
    if state_counts[ReviewConcernAttentionState.INFORMATIONAL] == total:
        return f"All {_conversation_count(total)} are informational."
    if state_counts[ReviewConcernAttentionState.OUTDATED] == total:
        return f"All {_conversation_count(total)} are marked outdated by observable GitHub metadata."
    if state_counts[ReviewConcernAttentionState.AUTHOR_REPLIED] == total:
        return f"The author replied to {_conversation_count(total)}; reviewer confirmation is not visible."
    if state_counts[ReviewConcernAttentionState.AUTHOR_DESCRIBED_CHANGES] == total:
        return f"The author described changes in {_conversation_count(total)}; reviewer verification is still needed."
    if state_counts[ReviewConcernAttentionState.AUTHOR_CLAIMED_ADDRESSED] == total:
        return f"The author claimed {_conversation_count(total)} addressed; reviewer confirmation is not visible."
    if state_counts[ReviewConcernAttentionState.AWAITING_AUTHOR_RESPONSE] == total:
        return f"{_sentence_start_count(total)} {_needs_need(total)} an author response."
    if state_counts[ReviewConcernAttentionState.REVIEWER_FOLLOW_UP] == total:
        return f"{_sentence_start_count(total)} {_needs_need(total)} reviewer follow-up after an author response."

    parts: list[str] = []
    if needing_attention:
        parts.append(f"{needing_attention} {_plural('review conversation', needing_attention)} {_needs_need(needing_attention)} attention")
    for state, label in (
        (ReviewConcernAttentionState.AWAITING_AUTHOR_RESPONSE, "awaiting author response"),
        (ReviewConcernAttentionState.AUTHOR_REPLIED, "with author replies"),
        (ReviewConcernAttentionState.AUTHOR_DESCRIBED_CHANGES, "where the author described changes"),
        (ReviewConcernAttentionState.AUTHOR_CLAIMED_ADDRESSED, "where the author claimed addressed"),
        (ReviewConcernAttentionState.REVIEWER_FOLLOW_UP, "with reviewer follow-up"),
        (ReviewConcernAttentionState.OUTDATED, "outdated"),
        (ReviewConcernAttentionState.INFORMATIONAL, "informational"),
        (ReviewConcernAttentionState.UNKNOWN, "unknown"),
    ):
        count = state_counts[state]
        if count:
            parts.append(f"{count} {label}")
    if active_change_requests:
        parts.append(f"{active_change_requests} latest change {_plural('request', active_change_requests)}")
    summary = "; ".join(parts).strip()
    return f"{summary}." if summary else "Review conversations were observed, but no specialized lifecycle summary applies."


def _conversation_count(count: int) -> str:
    return f"{count} {_plural('review conversation', count)}"


def _sentence_start_count(count: int) -> str:
    return f"{count} {_plural('review conversation', count)}"


def _plural(word: str, count: int) -> str:
    return word if count == 1 else f"{word}s"


def _needs_need(count: int) -> str:
    return "needs" if count == 1 else "need"


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
