# MergeSignal

MergeSignal is a deterministic GitHub pull-request risk analysis and merge-readiness platform. The current implementation includes a FastAPI backend, a React/Vite frontend, health checks, strict public GitHub PR URL parsing, GitHub REST data retrieval for public pull-request metadata, changed files, commits, read-only CI visibility for the pull-request head SHA, deterministic changed-file classification, deterministic review-signal detection, explainable merge-risk scoring, separate evidence-confidence scoring, deterministic merge-readiness decisions, deterministic changed-file review prioritization, and deterministic review actions.

Merge risk, evidence confidence, merge readiness, file priority, and review actions are separate deterministic outputs. Review actions are prompts for what humans should verify next, not AI commentary or generated fixes. MergeSignal does not currently assign reviewers, evaluate CODEOWNERS or repository policies, or claim that a pull request is safe or correct.

## Repository Layout

```text
backend/    FastAPI application, domain models, GitHub integration, settings, and tests
frontend/   React application, API client layer, and tests
docs/       Product scope, architecture, and API notes
```

## Prerequisites

- Python 3.11+; Python 3.13 is currently used for local verification
- Node.js 22 LTS; this repository standardizes on `>=22.12.0 <23`
- npm 10+

Use `nvm` from the repository root:

```bash
nvm use
```

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The backend health endpoint is available at `http://127.0.0.1:8000/health`.

Parse a public GitHub PR URL:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/pull-requests/parse \
  -H "Content-Type: application/json" \
  -d '{"url":"https://github.com/octocat/Hello-World/pull/1347?tab=files#discussion"}'
```

Fetch a public GitHub PR snapshot, including current head-SHA CI visibility, review signals, merge risk, evidence confidence, merge readiness, ranked changed files, and review actions:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/pull-requests/snapshot \
  -H "Content-Type: application/json" \
  -d '{"url":"https://github.com/octocat/Hello-World/pull/1347"}'
```

Optional GitHub token authentication can be configured in `backend/.env`:

```bash
GITHUB_TOKEN=
```

Leave `GITHUB_TOKEN` empty for unauthenticated public requests. Do not commit real token values.

Run backend tests:

```bash
cd backend
.venv/bin/python -m pytest
.venv/bin/python -m compileall app tests
```

## Frontend Setup

```bash
nvm use
cd frontend
npm install
cp .env.example .env
npm run dev
```

The frontend development server defaults to `http://127.0.0.1:5173`.

Run frontend checks:

```bash
cd frontend
npm test -- --run
npm run build
npm audit --audit-level=moderate
```

## Documentation

- [Product scope](docs/product-scope.md)
- [Architecture](docs/architecture.md)
- [API](docs/api.md)
- [Frontend](docs/frontend.md)
- [GitHub integration](docs/github-integration.md)
- [CI surface](docs/ci-surface.md)
- [File classification](docs/file-classification.md)
- [Review signals](docs/review-signals.md)
- [Scoring](docs/scoring.md)
- [Merge readiness](docs/merge-readiness.md)
- [File prioritization](docs/file-prioritization.md)
- [Review actions](docs/review-actions.md)

## Environment Configuration

Backend:

- `MERGE_SIGNAL_ENVIRONMENT`
- `MERGE_SIGNAL_PROJECT_NAME`
- `MERGE_SIGNAL_CORS_ORIGINS`
- `GITHUB_API_BASE_URL`
- `GITHUB_TOKEN`
- `GITHUB_REQUEST_TIMEOUT_SECONDS`
- `GITHUB_MAX_RETRIES`
- `GITHUB_RETRY_BASE_DELAY_SECONDS`
- `GITHUB_PER_PAGE`
- `GITHUB_MAX_PAGES`
- `GITHUB_USER_AGENT`

Frontend:

- `VITE_API_BASE_URL`

See `backend/.env.example` and `frontend/.env.example` for local defaults.

## Current Status

Implemented capabilities are limited to project foundation, health reporting, deterministic parsing of supported public GitHub PR URLs, retrieval of public GitHub pull-request metadata, changed files, commits, check runs, commit statuses, deterministic path-based file classification, deterministic review-signal detection, merge-risk assessment, evidence-confidence assessment, merge-readiness assessment, changed-file review prioritization, and deterministic review actions. Snapshot responses now include `signals`, `signal_summary`, `merge_risk`, `evidence_confidence`, `merge_readiness`, `ranked_files`, `file_priority_summary`, `review_actions`, and `review_action_summary`.

This foundation does not include required-check inference, reviewer assignment, CODEOWNERS evaluation, repository policy evaluation, generated fixes, generic AI code-review commentary, PostgreSQL, Redis, Docker Compose, GitHub OAuth, GitHub App installation flows, webhooks, background workers, CLI integration, or automated PR comments.
