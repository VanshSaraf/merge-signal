# Frontend

The MergeSignal frontend is a Vite React application that provides the end-to-end pull-request analysis flow and detailed report exploration for a single snapshot response.

## Architecture

The page is organized around focused modules:

- `src/api/pullRequests.js`: centralized snapshot API client for `POST /api/v1/pull-requests/snapshot`.
- `src/hooks/usePullRequestAnalysis.js`: analysis state, loading, error handling, retry support, and `AbortController` cancellation.
- `src/hooks/useTheme.js`: light/dark theme state, localStorage persistence, and system-theme default.
- `src/components/brand/`: original MergeSignal rabbit SVG mark.
- `src/components/layout/`: application header and pull-request report shell.
- `src/components/analysis/`: PR input, empty state, loading state, and the analysis dashboard shell.
- `src/components/report/`: report navigation, overview, ranked files, review signals, review actions, evidence, filters, score breakdowns, and file detail drawer.
- `src/components/common/`: reusable card, badge, skeleton, and error components.
- `src/hooks/useReportFilters.js`: derived client-side filtering and sorting for the existing snapshot payload.
- `src/utils/`: formatting, status-tone, and report helper utilities.

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
8. Successful responses render the detailed report from real backend data.

The frontend does not use fake pull requests, demo scores, simulated results, raw patch rendering, or credential values.

## Theme Behavior

The design is dark-first and also supports a polished light theme. CSS variables define canvas, elevated surfaces, panels, hover states, borders, text, accent, success, warning, danger, information, focus rings, shadows, radii, and spacing. The first visit respects the system color scheme. User preference is stored in `localStorage` under `mergesignal-theme`.

## Visual System

The frontend uses a compact developer-tool layout inspired by neutral code-hosting interfaces without copying GitHub branding, assets, or wording. The header contains the original two-tone MergeSignal rabbit mark, wordmark, backend health status, and theme toggle. The initial analysis form uses a command/search-bar treatment. Report state uses a pull-request identity header, compact assessment panels, bordered metric strips, file rows with monospace paths and diff-colored counts, signal disclosure panels, deterministic action prompts, and grouped evidence sections.

Most surfaces use small or medium radii, subtle borders, restrained shadows, and short transitions. Technical values such as paths, rule IDs, and branch names use a monospace stack.

## Report Scope

The current UI is a detailed snapshot report. It shows:

- repository and PR metadata
- readiness, risk, confidence, and CI status
- summary metrics
- merge-risk group and evidence-confidence score breakdowns
- all ranked files with priority, kind, area, status, search, sorting, and a detail drawer
- all review signals with severity, category, affected files, collapsible evidence, collapsible limitations, and rule IDs
- all review actions with priority, category, affected files, related signals, related readiness rules, evidence, limitations, and rule IDs
- readiness reasons, risk contributions, confidence components, completeness, CI, classification summary, and deduplicated limitations

The report is derived only from the `POST /api/v1/pull-requests/snapshot` response already returned by the backend. Client-side filters and sorting do not issue additional backend or GitHub requests. The file detail drawer shows classification evidence, previous-path classification for renames when available, priority factors, related signal IDs, and limitations; it does not show raw patches.

It does not yet provide history, comparison, CODEOWNERS, repository policies, reviewer assignment, PR comments, generated fixes, or GitHub publishing.

## Accessibility And Responsiveness

The UI uses semantic landmarks, labels, visible focus rings, accessible badge text, responsive grids, wrapping file paths, `tablist`/`tab`/`tabpanel` semantics, arrow/Home/End keyboard tab navigation, an Escape-closeable file detail drawer with focus return, and reduced-motion support. Decorative large mascot artwork is hidden from assistive technology.

Layouts are checked against desktop, tablet, and narrow mobile widths. Filters wrap, report navigation remains horizontally usable, file rows collapse into mobile-friendly cards, and the drawer becomes a full-width panel on small screens.

## Error Handling

The frontend distinguishes invalid URLs, not found responses, access-denied/private repository cases, GitHub rate limits, temporary upstream failures, backend unavailability, and unexpected response shapes where the backend provides enough signal. It never displays stack traces or raw internal errors.
