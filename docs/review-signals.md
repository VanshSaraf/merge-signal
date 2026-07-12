# Review Signals

## Purpose

Review signals are deterministic, evidence-backed observations derived from a normalized pull-request snapshot. They help reviewers navigate observable metadata, changed-file classification, CI visibility, and patch-level hints without claiming that a pull request is safe, unsafe, correct, or incorrect.

Signals are not a merge decision and do not prove code correctness. Signals feed merge-risk scoring through an explicit rule-ID weight registry, but signal severity is not automatically converted into risk points. Signals remain independently visible in snapshot responses even when they have zero scoring weight.

Readiness rules also consume selected signals through explicit rule IDs. Signals remain visible independently and are not automatically converted into readiness outcomes by severity alone.

See [Scoring](scoring.md) for merge-risk weights, caps, evidence-confidence components, and score thresholds. See [Merge readiness](merge-readiness.md) for readiness rules and precedence.

## Inputs Used

The signal engine uses only data already present in `PullRequestSnapshot`:

- Pull-request metadata.
- Changed-file metadata.
- Changed-file classifications.
- GitHub-provided patches when available.
- Commit metadata counts.
- Normalized CI state and visibility.
- Snapshot completeness information.

## Data Not Used

The engine does not clone repositories, open repository files from disk, fetch raw file contents, execute analyzed code, install dependencies, call external services, or send patch content outside the process.

## Model

Each `ReviewSignal` includes:

- `id`: deterministic signal identifier.
- `rule_id`: stable rule identifier.
- `title` and `description`: conservative explanation text.
- `category`: one primary category.
- `severity`: deterministic severity.
- `scope`: pull-request, file-set, file, CI, or snapshot scope.
- `affected_files`: unique sorted paths.
- `evidence`: structured safe evidence.
- `limitations`: relevant uncertainty.
- `tags`: stable lowercase labels.

`SignalEvidence` includes `kind`, `message`, optional `file`, optional sanitized `observed_value`, and optional `expected_context`. It never contains raw GitHub payloads, complete suspicious source lines, or suspected credential literal values.

## Severities

- `info`: contextual information for review navigation.
- `low`: minor review-quality or maintainability observation.
- `medium`: meaningful observable condition for deliberate review attention.
- `high`: sensitive or failure-related observable condition for strong attention.

There is no `critical`, `blocker`, or merge-blocking severity.

## Categories And Scopes

Categories are `metadata`, `change_scope`, `testing`, `ci`, `authentication`, `authorization`, `database`, `dependencies`, `api`, `infrastructure`, `configuration`, `security`, `code_quality`, `generated_content`, `rename`, and `completeness`.

Scopes are `pull_request`, `file_set`, `file`, `ci_surface`, and `snapshot`.

## Determinism

Rule IDs are stable strings such as `metadata.missing_description` and `security.credential_like_literal_added`. Signal IDs currently match rule IDs because the engine emits one aggregated signal per rule.

Signal ordering is deterministic:

1. Severity: `high`, `medium`, `low`, `info`.
2. Explicit category order from the signal enum.
3. Rule ID.
4. Signal ID.

Affected files are sorted case-insensitively with a stable tie-break. Evidence is deduplicated and sorted by kind, file, message, and sanitized observed value.

## Aggregation And Evidence Caps

The engine normally emits one signal per rule and aggregates all affected files and safe evidence. Evidence is capped at 25 items per signal. When evidence is capped, the signal limitations state that additional evidence was omitted.

Summary output includes total signal count, counts by severity and category, files with signals, high-attention files, patch-based signal count, metadata signal count, CI signal count, deduplicated warnings, and `rules_version`.

## Noise Control

Suppression rules are explicit:

- Very-large file-count suppresses large file-count.
- Very-large churn suppresses large churn.
- Sensitive change without test files suppresses generic production change without test files.
- CI unavailable suppresses CI missing.
- Migration-specific missing-patch visibility prevents duplicate opaque-patch evidence for that migration file.
- Dependency manifest without lockfile is aggregated once per rule with deduplicated evidence.
- Informational test-file presence is not emitted when deleted test files produce the stronger testing signal.

## Rule Families

Metadata rules cover missing PR descriptions, draft status, large commit count at 20 commits, and conservative GitHub merge-conflict observations.

Scope rules use thresholds of 25 changed files, 75 changed files, 1,000 changed lines, 3,000 changed lines, 500 changed lines in one file, and four significant functional areas. Documentation and generated areas are excluded from broad-area counting.

Sensitive-area rules use file classifications for authentication, authorization, database migrations, API paths, infrastructure, CI configuration, and conservative runtime configuration paths.

Testing rules identify production-relevant changes without changed test files, sensitive changes without changed test files, removed test files, changed test files as context, and test/documentation-only changes. These signals do not claim test coverage is known.

CI rules use normalized CI state and visibility: failing, pending, missing with complete visibility, unavailable visibility, partial visibility, and unknown observed outcomes.

Dependency rules cover manifest changes, lockfile changes, package manifest changes without a companion lockfile convention, and lockfile-only changes.

Database migration rules detect controlled destructive SQL pattern categories in added migration patch lines and report missing migration patch visibility.

Patch-level rules detect controlled debug statement patterns, TODO/FIXME comment markers, test skip patterns, lint or type suppressions, Python empty exception handler patterns, credential-like literal assignments, and security-control disable hints.

Rename rules compare current and previous classifications for moves into sensitive areas, moves out of test classification, and moves into generated classification.

Completeness rules surface incomplete patch coverage, changed-file collection, commit collection, and opaque binary or patchless changed files.

## Patch Scanning

Patch scanning uses only GitHub-provided patch strings. It separates added, removed, context, and metadata lines, excludes `+++`, `---`, and hunk headers from code scanning, and does not reconstruct complete files.

Bounds:

- 200,000 characters per patch.
- 10,000 lines per patch.
- 10,000 characters per line.

When a bound is reached, the engine emits a safe summary warning and continues with truncated scanning.

## Credential Safety

Credential-like literal detection is intentionally conservative. Evidence may include a file path and a safe label such as `password_like_literal` or `token_like_literal`, but suspected values and complete source lines are never returned.

The detector ignores common references such as environment lookups, GitHub Actions secrets references, placeholders, redacted values, empty values, and documentation/generated/asset/binary files.

## Versioning

The current rules version is `v1`. Rule changes that alter emitted signal semantics should update this version and synchronized tests/docs.

## Examples

Compact signal:

```json
{
  "id": "metadata.missing_description",
  "rule_id": "metadata.missing_description",
  "title": "Pull request description is missing",
  "category": "metadata",
  "severity": "low",
  "scope": "pull_request",
  "affected_files": [],
  "evidence": [
    {
      "kind": "metadata",
      "message": "Pull-request body is empty.",
      "file": null,
      "observed_value": "missing_description",
      "expected_context": null
    }
  ]
}
```

Compact summary:

```json
{
  "total_signals": 1,
  "counts_by_severity": [{"name": "low", "count": 1}],
  "counts_by_category": [{"name": "metadata", "count": 1}],
  "files_with_signals": [],
  "high_attention_files": [],
  "patch_based_signal_count": 0,
  "metadata_signal_count": 1,
  "ci_signal_count": 0,
  "warnings": [],
  "rules_version": "v1"
}
```

## Testing Strategy

Tests use local snapshot models, HTTPX mock transport, and FastAPI dependency overrides. They do not call the live GitHub API. Unit coverage checks deterministic ordering, suppression behavior, patch parsing, credential evidence sanitization, classification-based signals, CI signals, dependency rules, rename transitions, and summary consistency.

## Known Limitations

Signals can have false positives and false negatives because they are deterministic heuristics over bounded snapshot data. The engine does not understand business logic, does not validate vulnerabilities, does not confirm secrets, does not know complete test coverage, and does not determine merge readiness.
