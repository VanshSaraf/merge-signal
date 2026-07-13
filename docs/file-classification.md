# File Classification

## Current Scope

MergeSignal classifies changed-file paths as deterministic metadata during pull-request snapshot creation. The classifier uses only path strings returned by GitHub. It does not read files from disk, fetch file contents, clone repositories, execute repository code, or install dependencies.

Classification currently supports:

- Primary file kind, such as source, test, documentation, dependency manifest, dependency lockfile, database migration, CI configuration, infrastructure, generated, asset, binary, and unknown.
- Functional areas, such as frontend, backend, API, authentication, authorization, database, dependencies, CI/CD, infrastructure, testing, documentation, configuration, generated, security, and build tooling.
- Language or technology labels for common source, configuration, markup, infrastructure, and schema file extensions.
- Matched rule evidence with stable rule identifiers.
- A typed `context` object derived from observable path structure.
- Safe warnings for unknown classifications and unusual path shapes.
- Previous-path classification for renamed files.
- Pull-request-level summary counts across changed files.

## Determinism

Rules are static and order-independent except for the documented primary-kind precedence. Outputs are sorted by enum value or rule identifier where ordering matters. The classifier does not use AI, network access, repository contents, or local filesystem state.

Primary-kind precedence is:

1. Dependency lockfile
2. Dependency manifest
3. Database migration
4. CI configuration
5. Test
6. Documentation
7. Infrastructure
8. Configuration
9. Generated
10. Binary
11. Asset
12. Source
13. Unknown

This precedence lets specialized files remain specialized when multiple rules match. For example, `tests/fixtures/package-lock.json` remains a dependency lockfile, and `.github/workflows/README.md` remains CI configuration.

## Path Safety

Input paths are treated as untrusted repository-relative strings. The classifier normalizes matching with case-folding and forward-slash segments, but it never resolves paths. It emits warnings for unusually long paths, literal backslashes, leading slashes, repeated separators, control characters, and dot navigation segments.

## Path Context

`classification.context` adds bounded, path-derived context:

- `framework`, such as `nextjs_app_router` when an `app/**` route convention is visible.
- `component_role`, such as `route_page`, `route_layout`, `route_handler`, `loading_boundary`, `error_boundary`, `not_found_boundary`, `frontend_component`, `backend_controller`, or `backend_service`.
- `route_context`, including route groups and dynamic route markers.
- `access_context`, including observable protected route-group names.
- `domains`, extracted from meaningful path segments after reserved framework and generic segments are removed.
- boolean flags for user-facing, dynamic route, test, generated, configuration, documentation, and database-change context.
- context evidence and confidence.

Supported Next.js App Router conventions include:

- `app/**/page.js|jsx|ts|tsx`: route page
- `app/**/layout.*`: route layout
- `app/**/route.*`: route handler
- `app/**/loading.*`: loading boundary
- `app/**/error.*`: error boundary
- `app/**/not-found.*`: not-found boundary
- `[id]`, `[slug]`, and `[...path]`: dynamic route segments
- `(protected)`: route group and observable protected-route context
- `admin`: admin path context

Route groups and dynamic parameters are not product domains. MergeSignal does not infer authentication, public accessibility, or security guarantees from directory names.

## Domain Extraction

Domain extraction removes filenames, extensions, route groups, dynamic parameters, and generic segments such as `src`, `app`, `pages`, `components`, `lib`, `utils`, `services`, `api`, `tests`, and `test`.

For example, `app/(protected)/admin/cohort/[id]/page.tsx` produces domain `cohort`, admin/frontend context, protected route-group context, dynamic route context, and route-page role. It does not produce `(protected)`, `admin`, `[id]`, or `page` as product domains.

## API Shape

Each changed file in a snapshot includes:

- `classification`: classification for the current `filename`.
- `previous_classification`: classification for `previous_filename` when GitHub reports a rename; otherwise `null`.

The snapshot also includes `classification_summary` with total file counts, counts by kind, area, and language, renamed-file counts, missing-patch counts, and aggregate warnings.

Evidence confidence uses classification coverage as one visibility component. A file is considered meaningfully classified when either its primary kind or language is known. Functional area is not required for that confidence component.

## Non-Goals

- No merge decision.
- No merge-risk, readiness, or recommendation decision.
- No generated review commentary.
- No repository checkout, file-content inspection, arbitrary execution, or dependency installation.
- No claim that a recognized file kind proves a change is safe or unsafe.

## Future Use

The classification output feeds deterministic review-signal detection, merge-risk scoring, evidence-confidence scoring, merge-readiness decisions, and changed-file prioritization today. It is intended to feed later CODEOWNERS and policy evaluation. Later stages should consume the classification evidence instead of duplicating path heuristics inside route handlers.

The current review-signal engine consumes file kind, functional areas, language, matched rename classifications, and missing-patch context as snapshot evidence. Classification remains descriptive metadata; signals do not reinterpret classification as proof that a change is safe or unsafe.

Path context is not semantic code understanding. It uses only repository-relative path strings and existing changed-file metadata.
