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
- `app/services/` contains application services such as PR URL parsing.
- `app/models/` contains request, response, and API error models.
- `app/errors.py` contains the stable application error used by parser failures.
- `tests/` contains pytest coverage for API behavior.

The backend currently exposes `GET /health` and `POST /api/v1/pull-requests/parse`. Future PR-analysis modules should live behind dedicated service and API boundaries rather than inside route handlers.

## Request Sequence

```text
HTTP request
-> FastAPI versioned route
-> PR URL parser service
-> PullRequestReference domain model
-> typed API response
```

## Domain Layer

`PullRequestReference` represents only the normalized identity of a GitHub pull request: owner, repository, pull number, and canonical URL. It intentionally does not include GitHub API metadata such as title, author, commits, files, checks, or reviews.

## Parser Service

The parser accepts only supported public GitHub PR URLs and performs deterministic normalization. It validates scheme, host, authentication components, ports, path structure, decoded path segments, and pull number format separately. Query strings and fragments are ignored only after the base route is valid.

Parsing and GitHub fetching are separated because URL shape validation is a local trust-boundary concern, while future metadata retrieval will involve network access, rate limits, authentication policy, and response handling.

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

## Trust Boundary

The parse endpoint treats the incoming URL as untrusted input. It does not trim, repair, fetch, clone, execute, or install anything from the referenced repository.

Future GitHub client code should belong in a dedicated integration/service module separate from the parser and domain model.

## Frontend

The frontend is a Vite React application under `frontend/src`.

- `components/` contains reusable UI pieces.
- `pages/` contains route-level views.
- `services/` contains API configuration and request helpers.
- `test/` contains test setup.

React Router owns client-side navigation. The initial UI displays backend health with loading, success, and error states.

## Configuration

Backend configuration is loaded with Pydantic settings using the `MERGE_SIGNAL_` environment prefix. Frontend configuration uses Vite environment variables, currently `VITE_API_BASE_URL`.

## Future Boundaries

Planned backend areas:

- GitHub data collection for public pull-request metadata.
- Repository policy parsing.
- CODEOWNERS evaluation.
- Risk signal calculation.
- Evidence confidence scoring.
- Report serialization.

Planned infrastructure such as PostgreSQL, Redis, background workers, GitHub OAuth, GitHub App flows, and webhooks is intentionally excluded from this foundation.
