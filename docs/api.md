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

Parses a public GitHub PR URL, fetches pull-request metadata, changed files, commits, check runs, and commit statuses from the GitHub REST API, classifies changed-file path strings, detects deterministic review signals, calculates merge risk and evidence confidence, calculates merge readiness, ranks changed files by deterministic review priority, and returns a normalized snapshot. This endpoint does not perform required-check inference, recommendations, reviewer suggestions, CODEOWNERS evaluation, repository policy evaluation, or approval-state decisions.

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
    "files": [
      {
        "filename": "backend/app/main.py",
        "status": "modified",
        "additions": 5,
        "deletions": 1,
        "changes": 6,
        "patch": "@@ -1 +1 @@",
        "previous_filename": null,
        "blob_url": "https://github.com/owner/repository/blob/head/backend/app/main.py",
        "classification": {
          "primary_kind": "source",
          "areas": ["backend"],
          "language": "python",
          "matches": [
            {
              "rule_id": "kind.source.extension",
              "match_type": "extension",
              "value": ".py",
              "description": "Recognized source-code extension."
            }
          ],
          "warnings": []
        },
        "previous_classification": null
      }
    ],
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
    "classification_summary": {
      "total_files": 1,
      "classified_files": 1,
      "unknown_files": 0,
      "counts_by_kind": [{"name": "source", "count": 1}],
      "counts_by_area": [{"name": "backend", "count": 1}],
      "counts_by_language": [{"name": "python", "count": 1}],
      "renamed_files": 0,
      "files_with_previous_classification": 0,
      "files_without_patch": 0,
      "warnings": []
    },
    "signals": [
      {
        "id": "metadata.missing_description",
        "rule_id": "metadata.missing_description",
        "title": "Pull request description is missing",
        "description": "The pull-request body is empty after trimming.",
        "category": "metadata",
        "severity": "low",
        "scope": "pull_request",
        "affected_files": [],
        "evidence": [
          {
            "kind": "metadata",
            "message": "Pull-request body is empty.",
            "file": null,
            "observed_value": "missing_description",
            "expected_context": null
          }
        ],
        "limitations": ["A missing description does not imply the implementation is incorrect."],
        "tags": ["description", "metadata"]
      }
    ],
    "signal_summary": {
      "total_signals": 1,
      "counts_by_severity": [{"name": "low", "count": 1}],
      "counts_by_category": [{"name": "metadata", "count": 1}],
      "files_with_signals": [],
      "high_attention_files": [],
      "patch_based_signal_count": 0,
      "metadata_signal_count": 1,
      "ci_signal_count": 0,
      "warnings": [],
      "rules_version": "v1"
    },
    "merge_risk": {
      "score": 0,
      "level": "low",
      "max_score": 100,
      "group_scores": [
        {
          "group": "change_scope",
          "raw_points": 0,
          "applied_points": 0,
          "cap": 20,
          "capped_points": 0,
          "contribution_count": 0
        }
      ],
      "contributions": [],
      "contributing_signal_count": 0,
      "non_scoring_signal_count": 1,
      "rules_version": "v1",
      "limitations": ["Merge risk is a deterministic heuristic, not a probability."]
    },
    "evidence_confidence": {
      "score": 100,
      "level": "high",
      "max_score": 100,
      "components": [
        {
          "id": "pull_request_metadata",
          "name": "Pull-request metadata",
          "maximum_points": 15,
          "awarded_points": 15,
          "status": "complete",
          "explanation": "Core normalized pull-request metadata is present.",
          "limitations": ["Snapshot creation requires valid core metadata."]
        }
      ],
      "warnings": [],
      "rules_version": "v1",
      "limitations": ["Evidence confidence measures visibility and completeness, not code quality."]
    },
    "merge_readiness": {
      "decision": "ready",
      "decisive_rule_id": "readiness.ready_baseline",
      "reasons": [
        {
          "rule_id": "readiness.ready_baseline",
          "title": "No readiness concerns observed",
          "description": "No blocking, resolution-required, or caution condition was observed in the available snapshot.",
          "effect": "context",
          "observed_value": "no_readiness_concerns",
          "related_signal_ids": [],
          "affected_files": [],
          "explanation": "No blocking, resolution-required, or caution condition was observed in the available snapshot.",
          "limitations": ["Ready does not prove correctness or safety."]
        }
      ],
      "blocking_reason_count": 0,
      "resolution_reason_count": 0,
      "caution_reason_count": 0,
      "context_reason_count": 1,
      "rules_version": "v1",
      "limitations": ["A readiness decision is a deterministic heuristic, not proof of correctness."]
    },
    "ranked_files": [
      {
        "rank": 1,
        "path": "backend/app/main.py",
        "previous_path": null,
        "status": "modified",
        "score": 0,
        "level": "low",
        "primary_kind": "source",
        "areas": ["backend"],
        "language": "python",
        "changes": 6,
        "additions": 5,
        "deletions": 1,
        "related_signal_ids": [],
        "factors": [],
        "limitations": ["Review priority is a deterministic review-ordering heuristic, not a probability or defect score."]
      }
    ],
    "file_priority_summary": {
      "total_files": 1,
      "counts_by_level": [{"name": "low", "count": 1}],
      "highest_priority_files": ["backend/app/main.py"],
      "files_with_signal_factors": 0,
      "files_with_limited_patch_visibility": 0,
      "rules_version": "v1",
      "limitations": ["Review priority is a deterministic ordering heuristic, not merge risk."]
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
- `files`: changed files in GitHub order, each with deterministic current-path classification and previous-path classification for renames.
- `commits`: commits in GitHub order.
- `ci`: check runs, current commit statuses, aggregate CI state, visibility, counts, warnings, and CI completeness.
- `classification_summary`: counts and warnings across changed-file classifications.
- `signals`: deterministic review signals derived from snapshot data.
- `signal_summary`: counts and warnings across emitted review signals.
- `merge_risk`: deterministic merge-risk assessment derived from scoring review signals.
- `evidence_confidence`: deterministic evidence-confidence assessment derived from snapshot visibility.
- `merge_readiness`: deterministic merge-readiness assessment derived from normalized snapshot state, review signals, merge risk, and evidence confidence.
- `ranked_files`: every changed file once, ordered by deterministic review priority.
- `file_priority_summary`: counts and limitations for deterministic changed-file review priorities.
- `completeness`: booleans and warnings describing partial data.
- `rate_limit`: latest successful GitHub rate-limit headers when available.

CI state values are `passing`, `failing`, `pending`, `missing`, and `unknown`. CI visibility values are `complete`, `partial`, and `unavailable`.

File kind values are `source`, `test`, `documentation`, `configuration`, `dependency_manifest`, `dependency_lockfile`, `database_migration`, `ci_configuration`, `infrastructure`, `generated`, `asset`, `binary`, and `unknown`.

File area values are `frontend`, `backend`, `api`, `authentication`, `authorization`, `database`, `dependencies`, `ci_cd`, `infrastructure`, `testing`, `documentation`, `configuration`, `generated`, `security`, and `build_tooling`.

File language values are `python`, `javascript`, `typescript`, `java`, `c`, `cpp`, `csharp`, `go`, `rust`, `ruby`, `php`, `kotlin`, `swift`, `scala`, `sql`, `shell`, `powershell`, `html`, `css`, `scss`, `less`, `json`, `yaml`, `toml`, `xml`, `markdown`, `dockerfile`, `terraform`, `protobuf`, `graphql`, and `unknown`.

Signal severity values are `info`, `low`, `medium`, and `high`. Signal category values are `metadata`, `change_scope`, `testing`, `ci`, `authentication`, `authorization`, `database`, `dependencies`, `api`, `infrastructure`, `configuration`, `security`, `code_quality`, `generated_content`, `rename`, and `completeness`. Signal scope values are `pull_request`, `file_set`, `file`, `ci_surface`, and `snapshot`.

Signal evidence kinds are `metadata`, `file_path`, `file_count`, `line_count`, `classification`, `ci_state`, `ci_visibility`, `patch_pattern`, `rename_transition`, `completeness`, and `commit_count`.

Review signals are ordered deterministically by severity, category, rule ID, and signal ID. Affected files and evidence are deduplicated and sorted. Credential-like patch evidence never returns suspected literal values or full source lines.

Merge risk levels are `low`, `moderate`, `high`, and `very_high`. Score bounds are 0-100. Level thresholds are 0-24 low, 25-49 moderate, 50-74 high, and 75-100 very high.

Risk group values are `change_scope`, `sensitive_systems`, `testing`, `ci`, `operational_change`, and `code_quality`. Group caps are 20, 25, 15, 20, 15, and 5 respectively, totaling 100.

`MergeRiskAssessment` includes `score`, `level`, `max_score`, `group_scores`, `contributions`, `contributing_signal_count`, `non_scoring_signal_count`, `rules_version`, and `limitations`. `RiskGroupScore` includes `group`, `raw_points`, `applied_points`, `cap`, `capped_points`, and `contribution_count`. `RiskContribution` includes `signal_id`, `rule_id`, `group`, `title`, `severity`, `raw_points`, `applied_points`, `capped`, `affected_files`, and `explanation`.

Evidence confidence levels are `low`, `medium`, and `high`. Score bounds are 0-100. Level thresholds are 0-49 low, 50-79 medium, and 80-100 high.

`EvidenceConfidenceAssessment` includes `score`, `level`, `max_score`, `components`, `warnings`, `rules_version`, and `limitations`. `ConfidenceComponent` includes `id`, `name`, `maximum_points`, `awarded_points`, `status`, `explanation`, and `limitations`. Component statuses are `complete`, `partial`, `unavailable`, and `not_applicable`.

Scoring rules version is `v1`. Full weights, caps, confidence components, patch eligibility, and representative calculations are documented in [Scoring](scoring.md).

Merge-readiness decisions are `ready`, `ready_with_caution`, `not_ready`, and `blocked`. Decision effects are `block`, `require_resolution`, `caution`, and `context`.

`MergeReadinessAssessment` includes `decision`, `decisive_rule_id`, `reasons`, `blocking_reason_count`, `resolution_reason_count`, `caution_reason_count`, `context_reason_count`, `rules_version`, and `limitations`. `DecisionReason` includes `rule_id`, `title`, `description`, `effect`, `observed_value`, `related_signal_ids`, `affected_files`, `explanation`, and `limitations`.

Readiness rules version is `v1`. Full rule behavior, precedence, suppression, and representative scenarios are documented in [Merge readiness](merge-readiness.md).

File priority levels are `low`, `medium`, `high`, and `very_high`. Score bounds are 0-100. Level thresholds are 0-19 low, 20-39 medium, 40-69 high, and 70-100 very high.

`RankedFile` includes `rank`, `path`, `previous_path`, `status`, `score`, `level`, `primary_kind`, `areas`, `language`, `changes`, `additions`, `deletions`, `related_signal_ids`, `factors`, and `limitations`. `FilePriorityFactor` includes `id`, `category`, `points`, `description`, `related_signal_ids`, and `observed_value`.

File prioritization rules version is `v1`. Full factor groups, caps, ordering, and non-goals are documented in [File prioritization](file-prioritization.md).

The snapshot response intentionally does not include recommendations, required reviewers, reviewer suggestions, CODEOWNERS results, repository policy results, approval state, generated fixes, or probability claims.

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
- No CODEOWNERS parsing.
- No required-check inference.
- No recommendation engine, reviewer suggestion, approval state, generated fix, CODEOWNERS evaluation, or repository policy evaluation.
