# Review Context

MergeSignal collects observable GitHub pull-request review context as read-only snapshot evidence. It derives bounded review-concern attention states, but it does not determine whether concerns are formally resolved, code is fixed, or a PR is safe to merge.

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
| `concern_summary` | Deterministic lifecycle counts and attention summary for inline conversations. |
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

MergeSignal does not infer semantic relationships between separate threads. Lifecycle provenance remains thread-scoped.

## Concern Lifecycle

Each thread includes a `lifecycle` object with:

| Field | Meaning |
| --- | --- |
| `attention_state` | One of `awaiting_author_response`, `author_replied`, `author_claimed_addressed`, `reviewer_follow_up`, `outdated`, `informational`, or `unknown`. |
| `needs_attention` | Whether the observable state should prompt reviewer attention. |
| `verification_needed` | Whether an author claim still needs human verification. |
| `has_author_reply` | Whether the PR author replied after the root comment. |
| `has_reviewer_follow_up` | Whether a non-author participant replied after the latest author reply. |
| `author_claimed_addressed` | Whether bounded author wording claimed the concern was addressed. |
| `is_outdated` | Whether GitHub position metadata indicates the root comment is no longer current. |
| `resolution_visibility` | Currently always `unavailable`; REST data does not expose formal thread resolution. |
| `active_latest_change_request` | Whether the root reviewer currently has an observable latest `changes_requested` review state. |
| `approval_validity` | `current`, `potentially_stale`, or `unknown` based on visible review commit SHA and head SHA. |
| `summary` | Short deterministic explanation for the selected state. |
| `provenance` | Observable facts supporting the state decision. |

Author-addressed wording is deliberately bounded to complete words and short phrases such as `fixed`, `addressed`, `updated`, `resolved`, `done`, and `pushed a fix`. It is treated as a claim, not proof.

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

Review-context warnings and concern lifecycle states do not automatically change merge risk, evidence confidence, or merge readiness in this milestone.

The Review Briefing can surface current concern lifecycle states as reviewer focus items. Outdated conversations are preserved as historical context but are not treated as active briefing focus by themselves.

## Current Limitation

GitHub's REST review and review-comment endpoints do not expose true review-thread resolution state. MergeSignal therefore reports attention states and observable provenance, but does not label conversations formally resolved or unresolved. See [Review Concerns](review-concerns.md) for the lifecycle contract.
