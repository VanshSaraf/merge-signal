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

- No PR-existence verification.
- No GitHub Enterprise support.
- No GitHub network request in this milestone.
- No live GitHub metadata retrieval.
- No merge risk or evidence confidence calculation yet.
