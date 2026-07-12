# CI Surface

## Current Scope

MergeSignal reads read-only CI visibility for the current pull-request head SHA. It fetches:

- GitHub check runs for `GET /repos/{owner}/{repository}/commits/{head_sha}/check-runs`
- GitHub commit statuses for `GET /repos/{owner}/{repository}/statuses/{head_sha}`

The head SHA comes from pull-request metadata. MergeSignal does not inspect the base branch, branch names, older pull-request commits, guessed refs, or synthetic merge commits for CI data.

## Check Runs And Commit Statuses

Check runs represent GitHub Checks API records from any provider. Commit statuses represent status contexts attached to the commit SHA. MergeSignal keeps these surfaces separate because they have different GitHub semantics.

For repeated commit-status contexts, GitHub returns records in reverse chronological order. MergeSignal keeps only the newest record for each exact, case-sensitive context when calculating current CI state.

## Aggregate States

CI state values are `passing`, `failing`, `pending`, `missing`, and `unknown`.

Precedence:

1. `failing` when any current record is failing.
2. `pending` when none are failing and at least one is pending.
3. `unknown` when records exist but cannot be classified reliably.
4. `passing` when at least one current record exists and all records are passing, neutral, or skipped, with at least one passing record.
5. `missing` when both CI surfaces completed successfully and returned no records.

Neutral and skipped check runs are counted separately. A surface containing only neutral or skipped records is `unknown`, not strongly passing.

## Visibility

CI visibility values are `complete`, `partial`, and `unavailable`.

`missing` means GitHub returned no CI records from both surfaces successfully. `unavailable` means MergeSignal could not observe either CI surface and must not claim CI is absent.

The review-signal engine consumes these normalized values directly. It may emit CI signals for failing, pending, missing, unavailable, partial, or unknown observed outcomes, but it does not infer required checks or merge readiness.

CI visibility also feeds evidence confidence. Complete visibility awards full CI-visibility confidence points, partial visibility awards partial points, and unavailable visibility awards none. CI outcome does not change evidence confidence.

CI outcome affects merge risk only through explicit review signals such as `ci.failing`, `ci.pending`, `ci.missing`, or `ci.unknown_outcome`. Passing CI does not subtract merge risk and does not prove correctness.

## Partial Failures

Authentication failure and rate limiting remain global snapshot failures. Access denied, temporary unavailability, invalid CI responses, and pagination safety failures for one CI source can produce a successful snapshot with partial or unavailable CI visibility and warnings.

## Pagination And Rate Limits

CI requests reuse the existing GitHub pagination safety: only same-origin `rel="next"` links are followed, repeated links are rejected, and `GITHUB_MAX_PAGES` bounds the flow. Rate-limit metadata is parsed from GitHub headers and the latest successful response is exposed.

## Security

MergeSignal does not publish GitHub checks, update statuses, fetch workflow logs, fetch artifacts, infer required checks, clone repositories, execute code, or install dependencies. Tokens are optional and are not serialized in API responses.

## Testing

Automated tests use local fixtures, HTTPX `MockTransport`, and FastAPI dependency overrides. They do not call the live GitHub API.

## Limitations

- MergeSignal does not yet determine required checks.
- MergeSignal does not yet calculate merge readiness.
- MergeSignal does not publish GitHub checks or commit statuses.
- Passing CI does not prove correctness.
- CI visibility is one evidence-confidence component, not a merge decision.
