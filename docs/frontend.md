# Frontend

The MergeSignal frontend is a Vite React application that provides the first end-to-end pull-request analysis flow.

## Architecture

The page is organized around focused modules:

- `src/api/pullRequests.js`: centralized snapshot API client for `POST /api/v1/pull-requests/snapshot`.
- `src/hooks/usePullRequestAnalysis.js`: analysis state, loading, error handling, retry support, and `AbortController` cancellation.
- `src/hooks/useTheme.js`: light/dark theme state, localStorage persistence, and system-theme default.
- `src/components/analysis/`: PR input, empty state, loading state, and summary dashboard sections.
- `src/components/common/`: reusable card, badge, skeleton, and error components.
- `src/utils/`: formatting and status-tone helpers.

Visual components do not call the snapshot API directly.

## Local Startup

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

The frontend reads `VITE_API_BASE_URL` from `frontend/.env`. Local default:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Analysis Flow

1. The user enters a public GitHub pull-request URL.
2. The frontend performs lightweight empty/shape validation.
3. The backend remains the strict source of truth.
4. The frontend sends `POST /api/v1/pull-requests/snapshot`.
5. Loading skeletons display while the request is active.
6. The request can be cancelled.
7. Errors are shown with safe, user-readable messages.
8. Successful responses render the summary dashboard from real backend data.

The frontend does not use fake pull requests, demo scores, simulated results, raw patch rendering, or credential values.

## Theme Behavior

The design supports light and dark themes using CSS variables for backgrounds, panels, borders, text, status colors, spacing, radii, shadows, and focus rings. The first visit respects the system color scheme. User preference is stored in `localStorage` under `mergesignal-theme`.

## Dashboard Scope

The current UI is a summary dashboard. It shows:

- repository and PR metadata
- readiness, risk, confidence, and CI status
- summary metrics
- top ranked files
- review actions
- high and medium signals
- compact analysis limitations

It does not yet provide the complete detailed report, history, comparison, CODEOWNERS, repository policies, reviewer assignment, PR comments, generated fixes, or GitHub publishing.

## Accessibility And Responsiveness

The UI uses semantic landmarks, labels, visible focus rings, accessible badge text, responsive grids, wrapping file paths, and reduced-motion support. Tables are avoided in this milestone so mobile layouts remain readable without horizontal page overflow.

## Error Handling

The frontend distinguishes invalid URLs, not found responses, access-denied/private repository cases, GitHub rate limits, temporary upstream failures, backend unavailability, and unexpected response shapes where the backend provides enough signal. It never displays stack traces or raw internal errors.
