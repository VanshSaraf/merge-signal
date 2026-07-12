# API

## Base Path

The current versioned API base path is `/api/v1`. FastAPI also exposes OpenAPI at `/openapi.json` and Swagger UI at `/docs` in local development.

## GET /health

Returns application health and environment information.

Example:

```bash
curl http://127.0.0.1:8000/health
```

Response:

```json
{
  "status": "ok",
  "service": "MergeSignal",
  "environment": "local",
  "timestamp": "2026-07-12T00:00:00Z"
}
```

## POST /api/v1/pull-requests/parse

Parses and normalizes a public GitHub PR URL. This endpoint performs no GitHub network request and does not verify that the repository or pull request exists.

Request:

```json
{
  "url": "https://github.com/owner/repository/pull/123"
}
```

Success response:

```json
{
  "data": {
    "owner": "owner",
    "repository": "repository",
    "pull_number": 123,
    "canonical_url": "https://github.com/owner/repository/pull/123"
  }
}
```

Invalid URL response:

```json
{
  "error": {
    "code": "INVALID_PULL_REQUEST_URL",
    "message": "Provide a valid public GitHub pull-request URL."
  }
}
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/pull-requests/parse \
  -H "Content-Type: application/json" \
  -d '{"url":"https://github.com/octocat/Hello-World/pull/1347?tab=files#discussion"}'
```

## Validation

The request body must be a JSON object with a single string field named `url`. Unknown fields and non-string `url` values are rejected by FastAPI/Pydantic with a `422` validation response containing `detail`.

Unsupported or malformed PR URLs also return `422`, but use the stable MergeSignal error contract with `error.code` set to `INVALID_PULL_REQUEST_URL`.

## POST /api/v1/pull-requests/snapshot

Parses a public GitHub PR URL, fetches pull-request metadata, changed files, commits, check runs, and commit statuses from the GitHub REST API, and returns a normalized snapshot. This endpoint does not perform risk analysis, required-check inference, scoring, recommendations, or merge-readiness decisions.

Request:

```json
{
  "url": "https://github.com/owner/repository/pull/123"
}
```

Compact success response:

```json
{
  "data": {
    "reference": {
      "owner": "owner",
      "repository": "repository",
      "pull_number": 123,
      "canonical_url": "https://github.com/owner/repository/pull/123"
    },
    "metadata": {
      "number": 123,
      "title": "Pull request title",
      "body": null,
      "state": "open",
      "draft": false,
      "html_url": "https://github.com/owner/repository/pull/123",
      "author": {
        "login": "owner",
        "avatar_url": null,
        "html_url": "https://github.com/owner"
      },
      "base_branch": {
        "ref": "main",
        "sha": "base-sha",
        "repository_full_name": "owner/repository"
      },
      "head_branch": {
        "ref": "feature",
        "sha": "head-sha",
        "repository_full_name": "owner/repository"
      },
      "head_sha": "head-sha",
      "created_at": "2026-07-01T10:00:00Z",
      "updated_at": "2026-07-02T10:00:00Z",
      "closed_at": null,
      "merged_at": null,
      "additions": 12,
      "deletions": 4,
      "changed_files": 2,
      "commit_count": 2,
      "mergeable": null,
      "mergeable_state": null,
      "labels": ["backend"]
    },
    "files": [],
    "commits": [],
    "ci": {
      "state": "missing",
      "visibility": "complete",
      "check_runs": [],
      "commit_statuses": [],
      "total_check_runs": 0,
      "total_status_contexts": 0,
      "passing_count": 0,
      "failing_count": 0,
      "pending_count": 0,
      "neutral_count": 0,
      "skipped_count": 0,
      "warnings": [],
      "fetched_at": "2026-07-03T10:00:00Z",
      "completeness": {
        "check_runs_complete": true,
        "commit_statuses_complete": true,
        "check_run_pages_fetched": 1,
        "commit_status_pages_fetched": 1,
        "raw_status_record_count": 0,
        "unique_status_context_count": 0,
        "warnings": []
      },
      "rate_limit": {
        "limit": 5000,
        "remaining": 4998,
        "used": 2,
        "resource": "core",
        "reset_at": "2026-07-03T11:00:00Z"
      }
    },
    "completeness": {
      "files_complete": true,
      "commits_complete": true,
      "missing_patch_count": 0,
      "warnings": []
    },
    "fetched_at": "2026-07-03T10:00:00Z",
    "rate_limit": {
      "limit": 5000,
      "remaining": 4998,
      "used": 2,
      "resource": "core",
      "reset_at": "2026-07-03T11:00:00Z"
    }
  }
}
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/pull-requests/snapshot \
  -H "Content-Type: application/json" \
  -d '{"url":"https://github.com/octocat/Hello-World/pull/1347"}'
```

Custom error responses:

- `422 INVALID_PULL_REQUEST_URL`: the supplied URL is not a supported public GitHub PR URL.
- `404 GITHUB_PULL_REQUEST_NOT_FOUND`: GitHub returned `404`.
- `429 GITHUB_RATE_LIMITED`: GitHub rate limiting was detected.
- `403 GITHUB_ACCESS_DENIED`: GitHub denied access without a rate-limit signal.
- `502 GITHUB_AUTHENTICATION_FAILED`: GitHub rejected configured authentication.
- `502 GITHUB_INVALID_RESPONSE`: GitHub returned JSON or schema data MergeSignal cannot safely normalize.
- `502 GITHUB_PAGINATION_LIMIT_EXCEEDED`: pagination was unsafe or exceeded configured bounds.
- `502 GITHUB_REQUEST_FAILED`: an upstream GitHub request failed outside the more specific cases.
- `503 GITHUB_UNAVAILABLE`: GitHub transport, timeout, or transient `502`/`503`/`504` failures exhausted retries.

The request body must be a JSON object with a single string field named `url`. Unknown fields and non-string values are rejected with FastAPI/Pydantic `detail` validation responses.

Snapshot components:

- `reference`: normalized owner, repository, pull number, and canonical URL.
- `metadata`: pull-request metadata reported by GitHub.
- `files`: changed files in GitHub order.
- `commits`: commits in GitHub order.
- `ci`: check runs, current commit statuses, aggregate CI state, visibility, counts, warnings, and CI completeness.
- `completeness`: booleans and warnings describing partial data.
- `rate_limit`: latest successful GitHub rate-limit headers when available.

CI state values are `passing`, `failing`, `pending`, `missing`, and `unknown`. CI visibility values are `complete`, `partial`, and `unavailable`.

Normalized check-run fields include `id`, `name`, `status`, `conclusion`, provider name and slug, details URL, `started_at`, and `completed_at`.

Normalized commit-status fields include `id`, `context`, `state`, `description`, `target_url`, `creator_login`, `created_at`, and `updated_at`. Repeated status contexts are reduced to the newest record for the exact context.

`missing` means GitHub returned no CI records from both surfaces successfully. `unavailable` means MergeSignal could not observe either CI surface and must not claim CI is absent. Partial CI data is returned with warnings when one surface is unavailable.

## Supported URL Format

The supported URL format is:

```text
https://github.com/{owner}/{repository}/pull/{pull_number}
```

Only the public `github.com` host is supported. GitHub Enterprise hosts, GitHub API subdomains, and hosts that merely contain `github.com` are rejected.

## Normalization Rules

- The canonical URL always uses `https`.
- The canonical host is `github.com`.
- Owner and repository casing are preserved.
- Query parameters are removed.
- Fragments are removed.
- One trailing slash after the pull number is removed.
- The pull number must be a positive integer.

## Rejected URL Categories

MergeSignal rejects missing schemes, protocol-relative URLs, non-HTTPS schemes, authentication components, explicit ports, non-GitHub hosts, GitHub subdomains, repository homepages, issue URLs, commit URLs, compare URLs, actions URLs, missing path segments, invalid pull numbers, extra path segments, pull-request tab subpaths, duplicate route-changing separators, backslashes, encoded path separator tricks, malformed percent encoding, whitespace in path segments, and surrounding text.

## Current Limitations

- PR existence is verified only when `/snapshot` calls GitHub.
- No GitHub Enterprise support.
- No file classification or CODEOWNERS parsing.
- No required-check inference.
- No merge risk or evidence confidence calculation yet.
