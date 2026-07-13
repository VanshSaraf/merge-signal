# Frontend

The MergeSignal frontend is a Vite React application that provides the end-to-end pull-request analysis flow and detailed report exploration for a single snapshot response.

## Architecture

The page is organized around focused modules:

- `src/api/pullRequests.js`: centralized snapshot API client for `POST /api/v1/pull-requests/snapshot`.
- `src/hooks/usePullRequestAnalysis.js`: analysis state, loading, error handling, retry support, and `AbortController` cancellation.
- `src/hooks/useTheme.js`: light/dark theme state, localStorage persistence, and system-theme default.
- `src/components/brand/`: original MergeSignal rabbit SVG mark.
- `src/components/layout/`: application header and pull-request report shell.
- `src/components/landing/`: landing hero, command-style PR input, evidence pipeline schematic, capability overview, and trust boundaries.
- `src/components/analysis/`: loading state and the analysis dashboard shell.
- `src/components/report/`: report navigation, overview, ranked files, review conversations, review-concern lifecycle, review signals, review actions, evidence, filters, score breakdowns, and file detail drawer.
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

In production, `VITE_API_BASE_URL` is required and must point to the deployed backend. The configuration normalizes trailing slashes, rejects malformed URLs, and refuses localhost values in production. No secrets should be exposed through Vite variables.

For Vercel, set the project root to `frontend`. `frontend/vercel.json` keeps the build command, `dist` output directory, and React Router SPA fallback in one place.

## Landing And Analysis Entry

The entry page is a dark-first product surface for reviewers and maintainers. It leads with a single `h1`, a short explanation of MergeSignal's bounded analysis, three trust statements, and a command-style GitHub pull-request URL input. The input preserves keyboard submission, client-side shape validation, public-PR guidance, cancellation while loading, and a subtle backend availability indicator.

The adjacent schematic illustrates the real pipeline at a conceptual level: GitHub evidence, change classification, review signal detection, risk and confidence scoring, readiness, and review prioritization. It does not include fake repositories, fabricated scores, demo reports, screenshots, or simulated analysis output.

Below the hero, the page uses compact rows to explain merge readiness, risk versus evidence confidence, review prioritization, and traceable guidance. The trust section keeps the product boundaries visible: deterministic rules, bounded GitHub API usage, no repository execution, no dependency installation, sanitized errors, credential-like values withheld, and no AI-generated review commentary.

## Analysis Flow

1. The user enters a public GitHub pull-request URL.
2. The frontend performs lightweight empty/shape validation.
3. The backend remains the strict source of truth.
4. The frontend sends `POST /api/v1/pull-requests/snapshot`.
5. Bounded loading states keep the user oriented while the request is active.
6. The request can be cancelled.
7. Errors are shown with safe, user-readable messages.
8. Successful responses render the detailed report from real backend data.

The frontend does not use fake pull requests, demo scores, simulated results, raw patch rendering, or credential values.

## Theme Behavior

The design is dark-first and also supports a polished light theme. CSS variables define canvas, elevated surfaces, panels, hover states, borders, text, accent, success, warning, danger, information, focus rings, shadows, radii, and spacing. The first visit respects the system color scheme. User preference is stored in `localStorage` under `mergesignal-theme`.

## Visual System

The frontend uses a compact developer-tool layout inspired by neutral code-hosting interfaces without copying GitHub branding, assets, or wording. The global header contains the original two-tone MergeSignal rabbit mark, wordmark, repository/documentation links, backend health status, and theme toggle. The landing page uses a command-workbench composition rather than a generic marketing card. Report state uses a pull-request identity header, compact assessment panels, bordered metric strips, file rows with monospace paths and diff-colored counts, signal disclosure panels, deterministic action prompts, and grouped evidence sections.

Most surfaces use small or medium radii, subtle borders, restrained shadows, and short transitions. Technical values such as paths, rule IDs, and branch names use a monospace stack.

## Report Scope

The current UI is a detailed snapshot report. It shows:

- repository and PR metadata
- readiness, risk, confidence, and CI status
- compact CI surface intelligence with passing, failing, pending, and unknown counts
- expandable CI surface details with safe direct links when GitHub exposes HTTPS provider URLs
- observable review-state summary, concern lifecycle summary, and inline review conversations
- summary metrics
- merge-risk group and evidence-confidence score breakdowns
- all ranked files with priority, kind, area, status, search, sorting, and a detail drawer
- all review conversations with sanitized bounded text, ordered replies, participant names, attention states, lifecycle provenance, explicit verification limits, safe GitHub links, and hidden technical IDs
- all review signals with severity, category, affected files, collapsible evidence, collapsible limitations, and rule IDs
- all review actions with priority, category, affected files, related signals, related readiness rules, evidence, limitations, and rule IDs
- readiness reasons, risk contributions, confidence components, completeness, CI, classification summary, and deduplicated limitations

The report is derived only from the `POST /api/v1/pull-requests/snapshot` response already returned by the backend. Client-side filters and sorting do not issue additional backend or GitHub requests. The file detail drawer shows classification evidence, previous-path classification for renames when available, priority factors, related signal IDs, and limitations; it does not show raw patches.

It does not yet provide history, comparison, CODEOWNERS, repository policies, reviewer assignment, formal review-thread resolution detection, generated fixes, or GitHub publishing.

## Accessibility And Responsiveness

The UI uses semantic landmarks, labels, visible focus rings, accessible badge text, responsive grids, wrapping file paths, `tablist`/`tab`/`tabpanel` semantics, arrow/Home/End keyboard tab navigation, an Escape-closeable file detail drawer with focus return, and reduced-motion support. Decorative large mascot artwork is hidden from assistive technology.

Layouts are checked against desktop, tablet, and narrow mobile widths. Filters wrap, report navigation remains horizontally usable, file rows collapse into mobile-friendly cards, and the drawer becomes a full-width panel on small screens.

The mobile landing order is header, product label and headline, explanation, analysis command surface, trust statements, pipeline schematic, capability rows, and trust boundaries. Long pull-request URLs and file paths use wrapping constraints to avoid horizontal scrolling.

## Error Handling

The frontend distinguishes invalid URLs, not found responses, access-denied/private repository cases, GitHub rate limits, temporary upstream failures, backend unavailability, and unexpected response shapes where the backend provides enough signal. It never displays stack traces or raw internal errors.
