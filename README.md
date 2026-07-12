# MergeSignal

MergeSignal is a deterministic GitHub pull-request risk analysis and merge-readiness platform. The current implementation includes a FastAPI backend, a React/Vite frontend, health checks, and a versioned API endpoint for strict public GitHub PR URL parsing.

The pull-request analysis engine is intentionally not implemented yet.

## Repository Layout

```text
backend/    FastAPI application, domain models, parser service, settings, and tests
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

## Environment Configuration

Backend:

- `MERGE_SIGNAL_ENVIRONMENT`
- `MERGE_SIGNAL_PROJECT_NAME`
- `MERGE_SIGNAL_CORS_ORIGINS`

Frontend:

- `VITE_API_BASE_URL`

See `backend/.env.example` and `frontend/.env.example` for local defaults.

## Current Status

Implemented capabilities are limited to project foundation, health reporting, and deterministic parsing of supported public GitHub PR URLs into normalized pull-request references. The next planned milestone is live public GitHub metadata retrieval, kept separate from URL parsing.

This foundation does not include pull-request analysis, merge risk scoring, evidence confidence scoring, PostgreSQL, Redis, Docker Compose, GitHub OAuth, GitHub App installation flows, webhooks, background workers, CLI integration, or GitHub API fetching.
