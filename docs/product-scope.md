# Product Scope

## Problem

Pull requests can look easy to merge while still carrying hidden risk: sensitive files may be touched, ownership may be unclear, tests may not cover the changed surface, repository policies may be missed, or review evidence may be thin. MergeSignal will help teams understand merge readiness by surfacing deterministic, evidence-backed risk signals before a PR is merged.

## Bounded Initial Scope

The first version will analyze public GitHub pull requests using repository metadata, changed files, CODEOWNERS, branch and review policies, status checks, and explicit evidence available through supported GitHub surfaces. It will produce separate merge risk and evidence confidence outputs so teams can distinguish likely implementation risk from the strength of the supporting evidence.

The current implementation includes the project foundation, deterministic public GitHub PR URL parsing, GitHub REST retrieval for public pull-request metadata, changed files, commits, read-only CI visibility, deterministic path-based changed-file classification, and deterministic review-signal detection. It does not implement merge risk scoring, evidence confidence, or merge-readiness decisions.

## Non-Goals

- No arbitrary repository execution.
- No dependency installation from analyzed repositories.
- No automatic code modification or generated fixes.
- No generic AI-generated code-review commentary.
- No GitLab or Bitbucket support in the first version.
- No claim that MergeSignal proves a PR is bug-free.
- No private repository analysis in the initial public-PR scope.
- No replacement for human review, maintainership judgment, or release ownership.

## Main Product Outputs

- Merge risk score with deterministic supporting signals.
- Evidence confidence score that describes how much reliable evidence was available.
- Ranked changed-file list by expected review sensitivity.
- CODEOWNERS and repository policy evaluation.
- Human-readable merge-readiness summary grounded in collected evidence.
- Machine-readable report suitable for CLI and GitHub App integrations.

## Planned Implementation Phases

1. Project foundation: monorepo structure, backend and frontend shells, configuration, tests, and documentation.
2. PR URL parsing: strict public GitHub pull-request URL parsing and canonical pull-request references.
3. GitHub data ingestion: public pull-request metadata, changed files, and commits.
4. Read-only CI collection: check runs and commit statuses for the current pull-request head SHA.
5. Deterministic file classification: primary file kind, functional areas, languages, renamed-path classification, matched rule evidence, warnings, and summary counts.
6. Signal detection: deterministic rules for changed-file sensitivity, review evidence, CI visibility, dependency changes, migration hints, patch-level review hints, rename transitions, and completeness gaps.
7. Scoring model: separate merge risk and evidence confidence calculations with traceable explanations.
8. Interfaces: CLI workflow, web UI report exploration, and GitHub App integration.
9. Operational readiness: persistence, background processing, observability, rate-limit handling, and deployment hardening.
