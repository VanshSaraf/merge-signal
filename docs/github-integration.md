# GitHub Integration

## Current Capabilities

MergeSignal can fetch public GitHub pull-request metadata, changed files, commits, check runs, and commit statuses from the GitHub REST API after a PR URL passes the strict local parser. Changed-file path strings are classified locally after GitHub file data is normalized, deterministic review signals are produced from the completed snapshot, scoring is calculated from in-memory MergeSignal models, and merge readiness is calculated from the final normalized snapshot.

Supported input:

```text
https://github.com/{owner}/{repository}/pull/{pull_number}
```

GitHub Enterprise, private repositories, CODEOWNERS, policies, required-check inference, recommendations, file ranking, reviewer suggestions, and approval-state decisions are not implemented in this milestone.

## Authentication

`GITHUB_TOKEN` is optional. When it is empty, requests are unauthenticated and limited by GitHub's public rate limits. When configured, the client sends:

```text
Authorization: Bearer <token>
```

Token values are stored with Pydantic `SecretStr`, are not serialized in API responses, and should not be committed.

## Required Headers

The GitHub client sends:

- `Accept: application/vnd.github+json`
- `User-Agent: GITHUB_USER_AGENT`
- `X-GitHub-Api-Version: 2022-11-28`
- `Authorization: Bearer <token>` only when a token is configured

## Endpoints Used

- `GET /repos/{owner}/{repo}/pulls/{pull_number}`
- `GET /repos/{owner}/{repo}/pulls/{pull_number}/files`
- `GET /repos/{owner}/{repo}/pulls/{pull_number}/commits`
- `GET /repos/{owner}/{repo}/commits/{head_sha}/check-runs`
- `GET /repos/{owner}/{repo}/statuses/{head_sha}`

## Pagination

Changed files, commits, check runs, and commit statuses are fetched with `per_page=GITHUB_PER_PAGE`, starting at page 1. The client follows only safe `rel="next"` links that remain on the configured GitHub API host, rejects repeated next URLs, and enforces `GITHUB_MAX_PAGES`.

Ordering from GitHub is preserved.

## Retry Policy

Retries are bounded and deterministic. The client retries only:

- HTTPX transport errors
- timeouts
- HTTP `502`
- HTTP `503`
- HTTP `504`

It does not retry `400`, `401`, `403`, `404`, `422`, `429`, rate-limit responses, or schema-validation failures.

## Rate Limits

When present, these headers are normalized:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Used`
- `X-RateLimit-Resource`
- `X-RateLimit-Reset`

Malformed or absent rate-limit headers do not fail the request. The snapshot exposes metadata from the latest successful GitHub response in the flow.

## Error Mapping

- `404` -> `GITHUB_PULL_REQUEST_NOT_FOUND`
- `401` -> `GITHUB_AUTHENTICATION_FAILED`
- `403` or `429` with rate-limit evidence -> `GITHUB_RATE_LIMITED`
- `403` without rate-limit evidence -> `GITHUB_ACCESS_DENIED`
- exhausted timeout, transport, `502`, `503`, or `504` retries -> `GITHUB_UNAVAILABLE`
- invalid JSON or schema mismatch -> `GITHUB_INVALID_RESPONSE`
- unsafe pagination or page-limit exhaustion -> `GITHUB_PAGINATION_LIMIT_EXCEEDED`

## Completeness

The snapshot reports completeness without claiming analysis. Missing file patches are allowed because GitHub may omit patches for binary or very large files. Missing patches increment `missing_patch_count` and add a warning.

Changed-file classifications are based only on current and previous path strings. Review signals use snapshot metadata, classifications, normalized CI data, completeness data, and GitHub-provided patch strings when available. Scoring uses the resulting signals and snapshot visibility fields. Readiness uses the final normalized snapshot, signals, merge risk, and evidence confidence. These steps do not require repository checkout, file-content retrieval, additional GitHub requests, or dependency installation.

Warnings are also added when GitHub reports a changed-file or commit count that differs from the retrieved lists.

CI completeness is reported separately. Check-run `total_count` is compared with retrieved check runs, commit statuses are reduced to current unique contexts, and partial access or temporary CI-only failures are represented with warnings.

## Security

The client does not clone repositories, execute repository code, install dependencies, follow pagination to unrelated hosts, expose authorization headers, return raw GitHub payloads, publish check runs, update commit statuses, fetch workflow logs, fetch artifacts, or infer branch-protection required checks.

## Testing

Automated tests use HTTPX `MockTransport`, local fixtures, and FastAPI dependency overrides. They do not call the live GitHub API and do not require a real token.

Optional manual verification can be performed against a public PR by running the backend locally and calling `/api/v1/pull-requests/snapshot` with `curl`.
