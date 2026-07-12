# Architecture

## Overview

MergeSignal is organized as a small monorepo with independent frontend and backend applications. The current foundation favors explicit module boundaries and environment-driven configuration so future GitHub ingestion, signal evaluation, scoring, and integration layers can be added without reshaping the project.

## Backend

The backend is a FastAPI application under `backend/app`.

- `app/main.py` creates and exports the FastAPI application.
- `app/core/config.py` centralizes Pydantic settings.
- `app/api/health.py` owns the health endpoint.
- `tests/` contains pytest coverage for API behavior.

The backend currently exposes `GET /health` only. Future PR-analysis modules should live behind dedicated service and API boundaries rather than inside route handlers.

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

- GitHub data collection.
- Repository policy parsing.
- CODEOWNERS evaluation.
- Risk signal calculation.
- Evidence confidence scoring.
- Report serialization.

Planned infrastructure such as PostgreSQL, Redis, background workers, GitHub OAuth, GitHub App flows, and webhooks is intentionally excluded from this foundation.
