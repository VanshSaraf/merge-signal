# Review Context

MergeSignal collects observable GitHub pull-request review context as read-only snapshot evidence. It does not determine whether concerns are resolved, fixed, stale, or still actionable in this milestone.

## Collected Surfaces

The backend uses the existing GitHub REST client, timeout, retry, rate-limit, and pagination controls to fetch:

- `GET /repos/{owner}/{repository}/pulls/{pull_number}/reviews`
- `GET /repos/{owner}/{repository}/pulls/{pull_number}/comments`

It does not fetch issue comments, timeline events, CODEOWNERS, GraphQL review-thread resolution state, or repository policy data.

## Snapshot Field

The snapshot includes `review_context` with:

| Field | Meaning |
| --- | --- |
| `visibility` | `complete`, `partial`, or `unavailable`. |
| `completeness` | Separate retrieval flags, page counts, and warnings for reviews and inline comments. |
| `review_count` | Observable pull-request review count. |
| `comment_count` | Inline review-comment count after deduplication. |
| `thread_count` | Constructed inline conversation count. |
| `*_count` | Counts for approved, changes requested, commented, dismissed, and pending states. |
| `reviews` | Original observable review records with sanitized excerpts. |
| `latest_reviewer_states` | Latest observable submitted state per reviewer. |
| `threads` | Deterministic inline conversations with root comment and replies. |
| `warnings` | Partial-data and orphan-reply warnings. |
| `limitations` | Product boundaries for review context. |

## Thread Construction

Inline conversations are built deterministically:

- comments without `in_reply_to_id` become roots
- replies attach only to their referenced root comment
- orphan replies become standalone threads and produce a warning
- duplicate comments are deduplicated by GitHub comment ID
- comments are ordered by creation time, then identifier
- separate root comments are never merged just because they affect the same file

MergeSignal does not infer semantic relationships between separate threads.

## Review States

Review states are normalized from observable GitHub values:

- `approved`
- `changes_requested`
- `commented`
- `dismissed`
- `pending`
- `unknown`

Latest reviewer state is calculated by ordering each reviewer's records by submitted timestamp and ID. It is labeled as observable state only. MergeSignal does not claim an approval is still valid after later commits and does not claim a change request has been resolved.

## Safety

Review bodies and inline comments are user-generated content. MergeSignal:

- strips control characters
- removes simple unsafe markup
- redacts credential-like assignments
- bounds body excerpts
- never exposes raw diff hunks or patches
- never renders HTML directly in the frontend
- exposes only HTTPS `github.com` links without embedded credentials

Unsafe or malformed links are omitted.

## Completeness

Review-context visibility is independent from CI visibility and evidence confidence:

- `complete`: reviews and inline comments were both retrieved
- `partial`: one surface was retrieved and the other was unavailable or bounded by safety controls
- `unavailable`: neither surface was retrieved and no review/comment records were available

Review-context warnings do not automatically change merge risk, evidence confidence, or merge readiness in this milestone.

## Current Limitation

GitHub's REST review and review-comment endpoints do not expose true review-thread resolution state. MergeSignal therefore shows conversations and replies, but does not label them resolved or unresolved. Concern lifecycle, author-reply interpretation, and stale-comment logic are reserved for a later milestone.
