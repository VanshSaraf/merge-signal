# MergeSignal

MergeSignal is a deterministic GitHub pull-request risk analysis and merge-readiness platform. This repository currently contains only the project foundation: a FastAPI backend, a React/Vite frontend, and product/architecture documentation.

The pull-request analysis engine is intentionally not implemented yet.

## Repository Layout

```text
backend/    FastAPI application, settings, and tests
frontend/   React application, API client layer, and tests
docs/       Product scope and architecture notes
```

## Prerequisites

- Python 3.11+
- Node.js 20+
- npm 10+

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

Run backend tests:

```bash
cd backend
python -m pytest
```

## Frontend Setup

```bash
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
```

## Environment Configuration

Backend:

- `MERGE_SIGNAL_ENVIRONMENT`
- `MERGE_SIGNAL_PROJECT_NAME`
- `MERGE_SIGNAL_CORS_ORIGINS`

Frontend:

- `VITE_API_BASE_URL`

See `backend/.env.example` and `frontend/.env.example` for local defaults.

## Current Status

This foundation does not include PostgreSQL, Redis, Docker Compose, GitHub OAuth, GitHub App installation flows, webhooks, background workers, or GitHub API integration.
