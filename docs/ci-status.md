# CI Status Intelligence

MergeSignal observes two GitHub CI surfaces for the pull-request head SHA:

- check runs from the commit check-runs endpoint
- current commit statuses reduced by context

It does not infer required checks, branch protection, repository policy, or whether a provider should have run.

## Snapshot Fields

`ci` remains the normalized aggregate state and visibility record. `ci_explanation` adds an itemized explanation for UI and API consumers:

| Field | Purpose |
| --- | --- |
| `overall_state` | Aggregate CI state copied from `ci.state`. |
| `visibility` | Aggregate visibility copied from `ci.visibility`. |
| `summary` | Short explanation suitable for report overview copy. |
| `surfaces` | Provider/source groups for check runs and commit statuses. |
| `blocking_items` | Failing items that currently block readiness. |
| `*_count` | Passing, failing, pending, neutral, skipped, and unknown item counts. |

## Categories

Each item receives one deterministic category:

| Category | Typical evidence |
| --- | --- |
| `test` | Unit, integration, e2e, or spec check names. |
| `build` | Build, compile, or bundle check names. |
| `lint` | Linting tool names. |
| `typecheck` | Type-checking check names. |
| `deployment` | Deploy, preview, or Vercel deployment surfaces. |
| `authorization_or_configuration` | Authorization, permission, access, or configuration-required messages. |
| `security` | Security scanning and dependency-review checks. |
| `quality` | Coverage or quality surfaces. |
| `unknown` | No conservative category matched. |

Authorization/configuration is intentionally evaluated before deployment so a Vercel status such as `Authorization required to deploy.` is surfaced as a configuration blocker, not a generic deployment failure.

## Link Safety

Provider details links are included only when they are HTTPS URLs without embedded credentials. Unsafe values are omitted from `details_url` instead of being displayed.

## Duplicates And Partial Data

Commit statuses are already reduced to the current status per context by CI aggregation. The explanation layer also deduplicates exact repeated items by source type, provider, name, and safe details URL.

If one CI surface is unavailable, MergeSignal still returns the observed surface and marks visibility as partial. Partial visibility affects evidence confidence and review actions; it does not invent missing provider results.

## Review Briefing

The Review Briefing uses `ci_explanation.blocking_items` to identify specific blocking surfaces in the headline, focus list, and recommended steps. It uses the existing safe `details_url` when available and does not infer required checks or missing CI providers.

## Example

For a pull request with two passing GitHub Actions check runs and a failing Vercel commit status that says `Authorization required to deploy.`, MergeSignal reports:

| Assessment | Result |
| --- | --- |
| Overall CI | `failing` |
| Blocking item | `Vercel` |
| Category | `authorization_or_configuration` |
| Passed items | `2` |
| Readiness impact | Blocked by the failed Vercel authorization/configuration check. |
