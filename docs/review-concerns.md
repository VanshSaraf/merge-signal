# Review Concerns

MergeSignal derives a deterministic lifecycle for each inline review conversation using only observable GitHub REST review and review-comment data. This is an attention model, not a formal resolution model.

## Scope

The lifecycle model answers: "What should a reviewer look at next in this conversation?"

It does not answer whether the underlying code is correct, whether a reviewer accepted a fix, or whether GitHub considers a thread resolved.

## Attention States

| State | Meaning |
| --- | --- |
| `awaiting_author_response` | A non-author root comment has no later author reply. |
| `author_replied` | The PR author replied after the root comment without bounded addressed-claim wording. |
| `author_described_changes` | The PR author replied with bounded change-oriented wording such as changed this, moved, removed, added, updated, implemented, adjusted, now preserves, now only runs, or no longer runs. This requires reviewer verification and is not proof of resolution. |
| `author_claimed_addressed` | The PR author used bounded wording such as fixed, addressed, updated, resolved, or done. This is a claim only. |
| `reviewer_follow_up` | A non-author participant replied after the latest author reply. |
| `outdated` | GitHub position metadata indicates the root inline comment no longer has a current position. |
| `informational` | The root inline comment came from the PR author. |
| `unknown` | Available evidence is insufficient for a more specific lifecycle state. |

## Provenance

Each lifecycle includes provenance records for the facts used to derive the state, such as:

- root comment identity and author
- PR author identity when available
- author reply, change-description reply, or addressed-claim comment
- reviewer follow-up comment
- latest observable reviewer state
- head-SHA mismatch evidence for stale approval visibility

These records are intentionally thread-scoped so one conversation cannot borrow evidence from another.

## Summary Output

`review_context.concern_summary` reports total conversations, counts by attention state, conversations needing attention, active latest change requests, potentially stale approvals, and a concise deterministic summary.

The summary is displayed in the overview and reviews report sections. It does not change merge risk, evidence confidence, or merge readiness.

## Review Actions

Lifecycle state can create deterministic review actions:

- active latest change requests produce `action.review_concern.active_change_request`
- reviewer follow-ups produce `action.review_concern.reviewer_follow_up`
- awaiting-author conversations produce `action.review_concern.awaiting_author_response`
- author-described-change conversations produce `action.review_concern.verify_author_response` when no higher-priority lifecycle action applies
- author-claimed-addressed conversations produce `action.review_concern.verify_author_claim` when no higher-priority lifecycle action applies

Actions remain prompts for human review. They do not generate fixes or assert defects.

## Boundaries

MergeSignal does not use GitHub GraphQL review-thread resolution state in this milestone. It also does not:

- label conversations formally resolved or unresolved
- infer reviewer agreement from natural-language replies
- treat author-described changes as reviewer-confirmed fixes
- prove that author-claimed fixes changed the right code
- make approval validity decisions
- alter merge risk, evidence confidence, or readiness from lifecycle alone
- execute repository code, install dependencies, or modify analyzed repositories
