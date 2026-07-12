# Merge Readiness

Merge readiness is a deterministic decision derived from the normalized pull-request snapshot after review signals, merge risk, and evidence confidence have already been calculated. It produces one public decision and structured reasons that explain which rules matched.

Readiness is a heuristic, not proof of correctness. Ready does not mean safe or bug-free. Human review remains necessary. Decisions use only the evidence available in the snapshot, and passing CI does not prove correctness.

## Decision Values

- `ready`: no blocking, resolution-required, or caution condition was observed.
- `ready_with_caution`: no blocking or resolution-required condition was observed, but one or more caution conditions require deliberate human attention.
- `not_ready`: an observable condition should be resolved or completed before treating the pull request as ready.
- `blocked`: a concrete observable condition currently prevents normal merging or represents a directly failing merge gate.

## Effects And Precedence

Decision effects are:

- `block`
- `require_resolution`
- `caution`
- `context`

Precedence is explicit:

1. `block` -> `blocked`
2. `require_resolution` -> `not_ready`
3. `caution` -> `ready_with_caution`
4. `context` -> `ready`

The decisive rule is the highest-precedence matched rule, then the lowest configured priority within that effect, then stable rule ID.

## Blocking Rules

- `readiness.blocked.merge_conflict`: triggered by `metadata.merge_conflict_observed`.
- `readiness.blocked.ci_failing`: triggered by normalized failing CI or the `ci.failing` signal.

Blocked represents an observable current blocking condition. Failing CI with partial visibility remains blocked, and the partial visibility reason may still be shown.

## Not-Ready Rules

- `readiness.not_ready.draft`: pull request metadata or signal indicates draft status.
- `readiness.not_ready.ci_pending`: normalized CI state is pending.
- `readiness.not_ready.file_collection_incomplete`: changed-file collection is incomplete.
- `readiness.not_ready.ci_unavailable`: CI visibility is unavailable.
- `readiness.not_ready.low_evidence_confidence`: evidence confidence is low.
- `readiness.not_ready.credential_like_literal`: a credential-like literal signal was observed.
- `readiness.not_ready.security_control_disabled`: a security-control disabling signal was observed.
- `readiness.not_ready.very_high_risk`: merge risk is very high.

Not ready represents a condition requiring resolution or completion. Low evidence confidence can limit readiness without increasing merge risk.

## Caution Rules

- `readiness.caution.high_risk`: merge risk is high.
- `readiness.caution.moderate_risk`: merge risk is moderate.
- `readiness.caution.medium_evidence_confidence`: evidence confidence is medium.
- `readiness.caution.ci_missing`: CI visibility is complete and no CI records were observed.
- `readiness.caution.ci_unknown`: CI outcome could not be classified.
- `readiness.caution.ci_partial_visibility`: CI visibility is partial.
- `readiness.caution.patch_visibility_partial`: patch visibility is partial.
- `readiness.caution.commit_collection_incomplete`: commit collection is incomplete when low confidence has not already made it redundant.
- `readiness.caution.destructive_migration_hint`: a destructive migration pattern signal was observed.
- `readiness.caution.sensitive_change_without_tests`: sensitive-area changes were observed without changed test files.
- `readiness.caution.test_files_deleted`: test files were deleted.
- `readiness.caution.runtime_configuration_change`: runtime configuration changed.

Ready with caution requires deliberate human attention. Security-pattern signals remain heuristic and do not expose raw patch lines or suspected credential values.

## Ready Baseline

`readiness.ready_baseline` is emitted only when no block, resolution-required, or caution rule matches. It states that no readiness concern was observed in the available snapshot.

The typical ready case has low merge risk, high evidence confidence, passing and complete CI visibility, complete changed-file collection, complete commit collection, and no explicit caution signals.

## Structured Reasons

Each reason includes:

- `rule_id`
- `title`
- `description`
- `effect`
- `observed_value`
- `related_signal_ids`
- `affected_files`
- `explanation`
- `limitations`

Related signal IDs and affected files are deduplicated and sorted. Reasons do not contain recommendations, reviewer suggestions, raw source lines, suspected credential values, stack traces, probability fields, or file-priority ranking.

## Suppression

Suppression is explicit:

- Very-high risk uses `readiness.not_ready.very_high_risk` and does not emit high-risk or moderate-risk caution reasons.
- Low evidence confidence uses `readiness.not_ready.low_evidence_confidence` and does not emit medium-confidence caution.
- Unavailable CI suppresses missing-CI and unknown-CI caution.
- Failing CI does not suppress partial CI visibility.
- Ready baseline never coexists with stronger reasons.
- State-derived and signal-derived evidence for the same rule does not duplicate reasons.

## Interactions

Merge risk remains a separate assessment. Readiness reads the final `merge_risk` level and does not change risk scores, group scores, or contributions. See [Scoring](scoring.md) for weights and thresholds.

Evidence confidence remains a separate assessment. Readiness reads the final `evidence_confidence` level and components and does not change confidence scores, warnings, or components.

CI affects readiness through normalized CI state and visibility. Passing CI does not prove correctness. Missing, unknown, partial, pending, unavailable, and failing CI are handled by explicit rules with different effects.

Completeness affects readiness through changed-file collection, commit collection, patch visibility, and evidence confidence.

## Versioning

The current readiness rules version is `v1`. Rule changes that alter decision semantics should update the version and synchronized tests/docs.

## Representative Scenarios

- Merge conflict plus failing CI: `blocked`, decisive rule `readiness.blocked.merge_conflict`.
- Failing CI plus draft PR: `blocked`.
- Draft PR plus pending CI: `not_ready`, decisive rule `readiness.not_ready.draft`.
- Very-high risk plus medium confidence: `not_ready`.
- High risk plus medium confidence: `ready_with_caution`.
- Moderate risk plus high confidence: `ready_with_caution`.
- Low risk plus low confidence: `not_ready`.
- Low risk plus medium confidence: `ready_with_caution`.
- Low risk plus high confidence plus passing CI: `ready`.
- Low risk plus high confidence plus missing CI: `ready_with_caution`.

## Limitations

Ready does not mean safe or bug-free. Blocked does not describe every possible repository policy gate. Not ready does not imply the pull request is incorrect. Ready with caution does not prescribe an action.

File-priority ranking is calculated after readiness and does not change the readiness decision. No recommendation engine exists yet. No CODEOWNERS or policy evaluation exists yet.

## Testing Strategy

Tests cover domain validation, enum serialization, blocking rules, not-ready rules, caution rules, ready baseline behavior, precedence, suppression, deterministic ordering, reason counts, snapshot integration, OpenAPI exposure, risk/confidence immutability, and sanitized security reasons. API tests use local fixtures and dependency overrides with no live GitHub calls.

## Future Boundaries

Future milestones may add recommended reviewer actions, CODEOWNERS, repository policy configuration, history and comparison, GitHub App integration, and polished frontend reporting. Those features should consume readiness output through explicit models rather than changing the meaning of the four readiness decisions.
