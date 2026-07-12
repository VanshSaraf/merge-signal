# Architecture

## Overview

MergeSignal is organized as a small monorepo with independent frontend and backend applications. The current foundation favors explicit module boundaries and environment-driven configuration so future GitHub ingestion, signal evaluation, scoring, and integration layers can be added without reshaping the project.

## Backend

The backend is a FastAPI application under `backend/app`.

- `app/main.py` creates and exports the FastAPI application.
- `app/core/config.py` centralizes Pydantic settings.
- `app/api/health.py` owns the health endpoint.
- `app/api/v1/` owns versioned API routes.
- `app/domain/` contains domain models that do not depend on FastAPI route code.
- `app/services/` contains application services such as PR URL parsing, CI aggregation, and file classification.
- `app/signals/` contains deterministic review-signal rules, patch scanning, aggregation, and summary generation.
- `app/scoring/` contains deterministic merge-risk and evidence-confidence engines, rule weights, group caps, thresholds, and ordering helpers.
- `app/readiness/` contains deterministic merge-readiness rule metadata, precedence, suppression, and evaluation.
- `app/file_priority/` contains deterministic changed-file review-priority rules, factor caps, ordering, and summary generation.
- `app/review_actions/` contains deterministic review-action rules, ordering, aggregation, suppression, and summary generation.
- `app/integrations/github/` contains GitHub REST transport models, pagination, and the HTTPX client.
- `app/models/` contains request, response, and API error models.
- `app/errors.py` contains the stable application error used by parser failures.
- `tests/` contains pytest coverage for API behavior.

The backend currently exposes `GET /health`, `POST /api/v1/pull-requests/parse`, and `POST /api/v1/pull-requests/snapshot`. Future PR-analysis modules should live behind dedicated service and API boundaries rather than inside route handlers.

## Request Sequence

```text
HTTP request
-> FastAPI versioned route
-> PR URL parser service
-> PullRequestReference domain model
-> GitHub REST client when snapshot data is requested
-> changed-file retrieval
-> deterministic classification of changed-file path strings
-> commit retrieval
-> current head SHA from pull-request metadata
-> check-run and commit-status retrieval for that head SHA
-> deterministic review-signal engine
-> signal aggregation and summary generation
-> merge-risk engine
-> evidence-confidence engine
-> merge-readiness engine
-> file-priority engine
-> review-action engine
-> normalized PullRequestSnapshot domain model
-> typed API response
```

## Domain Layer

`PullRequestReference` represents only the normalized identity of a GitHub pull request: owner, repository, pull number, and canonical URL. Snapshot domain models represent normalized metadata, changed files, deterministic file classification, review signals, merge risk, evidence confidence, merge readiness, ranked changed files, review actions, commits, read-only CI visibility, completeness, fetch timestamp, and rate-limit metadata. They intentionally do not include required reviewers, approval state, CODEOWNERS results, repository policy results, generated patches, or merge commands.

## File Classification Service

The file classifier lives in `app/services/file_classifier.py` with rule data isolated in `app/services/file_classification_rules.py`. It accepts repository path strings from normalized changed files, returns strict domain models, and does not access the filesystem, network, repository contents, or local dependencies.

Classification output includes primary file kind, functional areas, language, matched rule evidence, safe warnings, previous-path classification for renames, and a pull-request-level summary. This is snapshot metadata only; it is not a merge-readiness decision or risk score.

## Review Signal Engine

The signal engine lives under `app/signals/`. Rule metadata and thresholds are centralized in `rules.py`; `patch_scanner.py` parses bounded GitHub patch strings; `engine.py` evaluates snapshot, file, CI, dependency, rename, completeness, and patch-level rules; `summary.py` builds deterministic counts.

The engine is pure application logic. It depends on typed snapshot models, does not depend on FastAPI or HTTPX, does not access the filesystem, does not access the network, does not mutate the input snapshot, and never fetches additional repository content. Patch evidence is sanitized so credential-like literal values and full suspicious source lines are not returned.

Signals are aggregated by stable rule ID. Affected files and evidence are deduplicated and sorted before serialization. The summary reports counts and high-attention files, but it is not a file ranking and does not include any numerical risk score.

## Scoring Engines

The scoring engines live under `app/scoring/` and consume already-normalized in-memory domain models. They do not depend on FastAPI, HTTPX, environment variables, filesystem access, network access, repository checkout, repository execution, dependency installation, or additional GitHub requests.

The merge-risk engine uses explicit rule-ID weights from `risk_rules.py`, applies group caps in a deterministic order, and returns `MergeRiskAssessment`. Group caps are centralized and total 100: change scope 20, sensitive systems 25, testing 15, CI 20, operational change 15, and code quality 5.

The evidence-confidence engine uses snapshot completeness, patch visibility, CI visibility, and classification coverage. It returns `EvidenceConfidenceAssessment` and never changes merge risk. CI outcome affects merge risk only through explicit review signals; CI visibility affects evidence confidence.

Scoring runs after review-signal detection and signal summary generation:

```text
GitHub data
-> normalized snapshot
-> CI normalization
-> file classification
-> review signals
-> signal summary
-> merge-risk engine
-> evidence-confidence engine
-> merge-readiness engine
-> file-priority engine
-> review-action engine
-> PullRequestSnapshot response
```

There is no circular dependency between signal detection and scoring. Signals remain independently visible in the response, and scoring does not mutate signal collections.

## Readiness Engine

The readiness engine lives under `app/readiness/` and consumes final in-memory snapshot state, review signals, merge risk, and evidence confidence. It does not recalculate scoring and does not mutate signals, risk contributions, confidence components, CI data, completeness data, or classifications.

The engine returns exactly one decision: `ready`, `ready_with_caution`, `not_ready`, or `blocked`. Rule effects have explicit precedence: block, require resolution, caution, then context. Readiness performs no filesystem access, no network access, no additional GitHub requests, no repository execution, no dependency installation, no recommendations, and no file-priority calculation.

## File-Priority Engine

The file-priority engine lives under `app/file_priority/` and consumes the in-memory snapshot after readiness has been calculated. It returns `ranked_files` and `file_priority_summary`, and it does not change classifications, review signals, merge risk, evidence confidence, readiness, CI, or completeness.

File priority is separate from merge risk. It is a deterministic review-ordering heuristic for changed files, not a probability, defect score, recommendation engine, reviewer assignment engine, CODEOWNERS evaluator, or policy evaluator. It performs no filesystem access, no network access, no additional GitHub requests, no repository execution, and no dependency installation.

## Review-Action Engine

The review-action engine lives under `app/review_actions/` and consumes the completed in-memory snapshot after file prioritization. It returns `review_actions` and `review_action_summary`, and it does not mutate signals, readiness reasons, risk contributions, confidence components, ranked files, CI, completeness, or classifications.

Review actions are deterministic human-review prompts, not AI commentary, generated fixes, reviewer assignments, or probability claims. The engine uses explicit rule IDs only, aggregates related evidence, suppresses repetitive CI and testing prompts, sanitizes security evidence, and performs no filesystem access, no network access, no additional GitHub requests, no repository execution, and no dependency installation.

## Parser Service

The parser accepts only supported public GitHub PR URLs and performs deterministic normalization. It validates scheme, host, authentication components, ports, path structure, decoded path segments, and pull number format separately. Query strings and fragments are ignored only after the base route is valid.

Parsing and GitHub fetching are separated because URL shape validation is a local trust-boundary concern, while future metadata retrieval will involve network access, rate limits, authentication policy, and response handling.

## GitHub Integration Boundary

GitHub-specific transport models live under `app/integrations/github/models.py` and ignore unknown upstream fields. Internal domain models remain strict and explicit. The route layer never returns raw GitHub dictionaries.

`GitHubRestClient` owns one HTTPX `AsyncClient` for a complete snapshot request. FastAPI provides it through dependency injection, which lets tests replace the client without patching transport internals. The client closes owned HTTPX clients after the request lifecycle.

CI retrieval uses only `metadata.head_sha`. Check runs are fetched from the commit check-runs endpoint and commit statuses from the commit statuses endpoint. The route layer does not pass arbitrary refs to CI retrieval.

The CI aggregation service lives outside FastAPI. It reduces check-run outcomes and current commit-status contexts into state and visibility values without making merge-readiness claims. Partial CI-only failures can produce a successful snapshot with warnings, while authentication and rate-limit failures remain global errors.

Pagination is centralized in `app/integrations/github/pagination.py`. Only safe `rel="next"` links on the configured API host are followed, repeated links are rejected, and `GITHUB_MAX_PAGES` bounds the flow.

Retries are limited to HTTPX transport errors, timeouts, and transient `502`/`503`/`504` responses. Authentication, authorization, not-found, rate-limit, and schema errors are not retried.

## API Models And Errors

Request and response models live under `app/models/`. Unknown request fields are rejected. Unsupported or malformed PR URLs are mapped to a stable JSON error contract:

```json
{
  "error": {
    "code": "INVALID_PULL_REQUEST_URL",
    "message": "Provide a valid public GitHub pull-request URL."
  }
}
```

FastAPI/Pydantic request-validation errors remain distinguishable because they use the framework `detail` response shape.

## Dependency Direction

Routes may depend on API models, services, and application errors. Services may depend on domain models and application errors. Domain models do not depend on routes, services, or FastAPI.

GitHub integration code may depend on settings, transport models, domain models, and application errors. Routes depend on the GitHub client through FastAPI dependency injection rather than HTTPX directly.

## Trust Boundary

The parse endpoint treats the incoming URL as untrusted input. It does not trim, repair, fetch, clone, execute, or install anything from the referenced repository.

The snapshot endpoint may fetch public data from the configured GitHub REST API host after parsing succeeds. It does not clone repositories, execute repository code, install dependencies, inspect repository files from disk, send patches to external services, or follow pagination links to unrelated hosts.

## Frontend

The frontend is a Vite React application under `frontend/src`.

- `api/` contains the centralized pull-request snapshot API client.
- `components/` contains reusable UI pieces.
- `components/report/` contains detailed snapshot report sections, filters, score breakdowns, and the file detail drawer.
- `hooks/` contains analysis and theme state.
- `pages/` contains route-level views.
- `services/` contains API configuration and request helpers.
- `test/` contains test setup.
- `utils/` contains formatting and status helpers.

React Router owns client-side navigation. The current home page provides the end-to-end pull-request analysis flow: URL input, loading and cancellation, safe error rendering, and a detailed report built only from real snapshot responses. Report tabs cover overview, ranked files, review signals, review actions, and evidence/limitations. Client-side filtering and sorting operate on the received snapshot payload and do not trigger extra backend or GitHub requests.

## Configuration

Backend configuration is loaded with Pydantic settings using the `MERGE_SIGNAL_` environment prefix. Frontend configuration uses Vite environment variables, currently `VITE_API_BASE_URL`.

## Future Boundaries

Planned backend areas:

- Repository policy parsing.
- CODEOWNERS evaluation.
- Report exploration.
- Reviewer assignment and repository-policy actions.
- Report serialization.

Planned infrastructure such as PostgreSQL, Redis, background workers, GitHub OAuth, GitHub App flows, and webhooks is intentionally excluded from this foundation.
