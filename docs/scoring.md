# Scoring

MergeSignal calculates two separate deterministic scores after review signals have been generated:

- Merge risk: a bounded indicator of review attention justified by observed signals.
- Evidence confidence: an indicator of how complete and observable the analysis surface was.

The scores are separate because a pull request can have strong observed risk signals with incomplete evidence, or complete evidence with few scoring signals. Evidence confidence never changes merge risk, and merge risk never changes evidence confidence.

Scores are deterministic heuristics, not probabilities. Merge risk is not a merge decision. A low merge-risk score does not mean a pull request is safe. High evidence confidence does not mean the code is correct. Passing CI does not prove correctness.

## Merge Risk

Merge risk uses normalized review signals only. It does not use evidence confidence, raw GitHub payloads, hidden repository state, CODEOWNERS, branch policies, required-check inference, repository execution, dependency installation, generated fixes, or AI commentary.

The score is an integer from 0 to 100 with these levels:

- `low`: 0-24
- `moderate`: 25-49
- `high`: 50-74
- `very_high`: 75-100

Rules version: `v1`.

## Risk Groups And Caps

Group caps prevent overlapping signals from dominating the score:

- `change_scope`: 20
- `sensitive_systems`: 25
- `testing`: 15
- `ci`: 20
- `operational_change`: 15
- `code_quality`: 5

The caps total 100. Every `RiskGroupScore` is present in this stable order, including groups with zero points.

## Rule Weights

Weights are explicit by review-signal rule ID. Severity is not automatically converted to points.

Change scope:

- `scope.large_file_count`: 8
- `scope.very_large_file_count`: 15
- `scope.large_line_churn`: 8
- `scope.very_large_line_churn`: 15
- `scope.large_individual_file_change`: 6
- `scope.broad_functional_change`: 8
- `metadata.large_commit_count`: 3

Sensitive systems:

- `authentication.paths_changed`: 10
- `authorization.paths_changed`: 10
- `database.migration_changed`: 10
- `database.destructive_migration_hint`: 15
- `api.surface_changed`: 6
- `security.credential_like_literal_added`: 18
- `security.security_control_disabled_hint`: 15
- `rename.file_moved_into_sensitive_area`: 7

Testing:

- `testing.production_change_without_test_files`: 7
- `testing.sensitive_change_without_test_files`: 12
- `testing.test_files_deleted`: 12
- `testing.test_skip_added`: 10

CI:

- `ci.failing`: 18
- `ci.pending`: 6
- `ci.missing`: 8
- `ci.unavailable`: 6
- `ci.partial_visibility`: 4
- `ci.unknown_outcome`: 5

Operational change:

- `dependencies.manifest_changed`: 4
- `dependencies.lockfile_changed`: 1
- `dependencies.manifest_without_lockfile`: 7
- `dependencies.lockfile_only_change`: 0
- `infrastructure.configuration_changed`: 7
- `ci.configuration_changed`: 6
- `configuration.runtime_configuration_changed`: 5
- `database.migration_without_patch_visibility`: 6
- `rename.file_moved_out_of_test_area`: 6

Code quality:

- `code_quality.debug_statement_added`: 2
- `code_quality.todo_or_fixme_added`: 1
- `code_quality.lint_or_type_suppression_added`: 3
- `code_quality.empty_exception_handler_added`: 4
- `generated_content.large_generated_change`: 2
- `completeness.opaque_files_changed`: 2
- `rename.file_moved_into_generated_area`: 1

Explicit zero-point signals:

- `metadata.draft_pull_request`
- `metadata.missing_description`
- `testing.test_files_changed`
- `testing.only_test_or_documentation_changes`
- `generated_content.generated_files_changed`
- `completeness.file_collection_incomplete`
- `completeness.commit_collection_incomplete`
- `completeness.patch_coverage_incomplete`

Unknown future signal IDs are treated as non-scoring, remain visible in `signals`, increment `non_scoring_signal_count`, and do not fail scoring.

## Cap Application Order

Within each risk group, contributions are sorted by:

1. Higher configured raw weight.
2. Higher signal severity.
3. Stable rule ID.
4. Stable signal ID.

Points are applied until the group cap is reached. The contribution that crosses the cap receives the remaining points and is marked `capped`. Later contributions receive `applied_points: 0`, remain visible as risk contributions, and are marked `capped`.

`raw_points` is the configured rule weight. `applied_points` is the portion remaining after the cap. `capped_points` on the group equals `raw_points - applied_points`.

## Evidence Confidence

Evidence confidence uses snapshot visibility and completeness only. It does not use merge-risk score, signal severity, CI outcome, future CODEOWNERS support, repository policy support, or unimplemented integrations.

The score is an integer from 0 to 100 with these levels:

- `low`: 0-49
- `medium`: 50-79
- `high`: 80-100

Rules version: `v1`.

Components total 100:

- `pull_request_metadata`: 15
- `changed_file_collection`: 25
- `patch_visibility`: 25
- `commit_collection`: 10
- `ci_visibility`: 15
- `classification_coverage`: 10

Statuses are `complete`, `partial`, `unavailable`, and `not_applicable`.

## Confidence Components

Pull-request metadata awards 15 when normalized core metadata exists. Snapshot creation requires this metadata.

Changed-file collection awards:

- complete collection: 25
- incomplete collection with some files: 10
- unavailable collection: 0

Patch visibility is calculated only across patch-eligible files. Patch-ineligible files are `asset`, `binary`, and `generated` files. If no patch-eligible files exist, the component is `not_applicable` and awards 25 as a neutral treatment.

Patch visibility awards:

- 100%: 25
- 80-99%: 20
- 50-79%: 12
- 1-49%: 5
- 0%: 0

Commit collection awards:

- complete collection: 10
- incomplete collection with some commits: 4
- unavailable collection: 0

CI visibility awards:

- `complete`: 15
- `partial`: 8
- `unavailable`: 0

CI state does not affect evidence confidence. A complete `missing` CI state still receives 15 because MergeSignal successfully observed that no CI records were present.

Classification coverage considers a file meaningfully classified when either `primary_kind` is not `unknown` or `language` is not `unknown`. Functional area is not required.

Classification coverage awards:

- no changed files: 10
- 100%: 10
- 80-99%: 8
- 50-79%: 5
- 1-49%: 2
- 0%: 0

Warnings are deterministic and deduplicated for incomplete changed-file collection, incomplete commit collection, partial patch visibility, partial or unavailable CI visibility, and limited classification coverage.

## Representative Calculations

Documentation-only PR:

- Signal `testing.only_test_or_documentation_changes` has zero risk weight.
- Merge risk: 0, `low`.
- Complete evidence confidence: 100, `high`.

Large PR with broad functional change:

- `scope.very_large_file_count` 15 and `scope.very_large_line_churn` 15 raw points share the `change_scope` cap.
- Raw group points: 30.
- Applied group points: 20.

Authentication, authorization, and credential-like literal:

- Raw points: 10 + 10 + 18 = 38 in `sensitive_systems`.
- Applied points: 25 because of the group cap.

Failing CI with partial visibility:

- Raw points: `ci.failing` 18 + `ci.partial_visibility` 4 = 22.
- Applied points: 20 because of the CI cap.

High risk with high confidence:

- Complete snapshot evidence with destructive migration, failing CI, and sensitive testing signals can produce high merge risk and high evidence confidence.

High risk with low confidence:

- Strong observed sensitive-system and CI signals can produce high merge risk while incomplete files, missing patches, and unavailable CI lower evidence confidence.

Low risk with high confidence:

- Complete documentation-only or test/documentation-only changes can produce low merge risk and high evidence confidence.

Low risk with low confidence:

- Sparse incomplete observable data with no scoring signals can produce low merge risk and low evidence confidence.

## API Models

`MergeRiskAssessment` includes `score`, `level`, `max_score`, `group_scores`, `contributions`, `contributing_signal_count`, `non_scoring_signal_count`, `rules_version`, and `limitations`.

`RiskGroupScore` includes `group`, `raw_points`, `applied_points`, `cap`, `capped_points`, and `contribution_count`.

`RiskContribution` includes `signal_id`, `rule_id`, `group`, `title`, `severity`, `raw_points`, `applied_points`, `capped`, `affected_files`, and `explanation`.

`EvidenceConfidenceAssessment` includes `score`, `level`, `max_score`, `components`, `warnings`, `rules_version`, and `limitations`.

`ConfidenceComponent` includes `id`, `name`, `maximum_points`, `awarded_points`, `status`, `explanation`, and `limitations`.

Snapshot responses include merge readiness as a separate assessment built after merge risk and evidence confidence. Readiness does not change risk scores or confidence scores. See [Merge readiness](merge-readiness.md) for decision rules and precedence.

The snapshot response does not include recommendations, ranked files, required reviewers, approval state, CODEOWNERS results, repository policy results, generated fixes, or probability claims.

## Determinism And Boundaries

Scoring operates on in-memory MergeSignal models after normalized metadata, changed files, file classifications, commits, CI, completeness, review signals, and signal summary are available. It performs no filesystem access, no network access, no repository checkout, no repository execution, no dependency installation, and no additional GitHub requests.

The scoring engines do not mutate input signals or snapshot collections. Ordering is deterministic across group scores, contributions, components, warnings, affected files, and limitations.

## Testing Strategy

Tests cover enum serialization, score bounds, invalid point combinations, risk registry validity, cap totals, group cap allocation, level boundaries, representative risk scenarios, unknown signal behavior, confidence thresholds, patch eligibility, CI visibility independence from CI outcome, classification coverage, risk/confidence separation, snapshot integration, and OpenAPI exposure. API tests use local fixtures and dependency overrides with no live GitHub calls.

## Future Extension Boundaries

Future milestones may add file prioritization, CODEOWNERS, repository policies, required-check inference, CLI output, polished frontend reporting, or GitHub App publishing. Those features should consume the existing scoring and readiness output through explicit models rather than changing the meaning of merge risk or evidence confidence.
