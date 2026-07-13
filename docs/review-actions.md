# Review Actions

Review actions are deterministic prompts that describe what a human reviewer should verify next. They are derived from existing snapshot evidence after review signals, scoring, readiness, and file prioritization are complete.

Actions are deterministic review prompts, not AI commentary. Actions do not prove a defect, do not modify code, do not assign reviewers, and do not evaluate CODEOWNERS or repository policies. Human judgment remains required.

## Output

Snapshot responses include:

- `review_actions`: deduplicated review prompts with priority, category, related signals, related readiness rules, affected files, safe evidence, and limitations.
- `review_action_summary`: counts by priority and category, affected-file count, high-priority action count, rule version, and limitations.

The Review Briefing may reuse selected actions as recommended steps, but it does not convert every action into a focus item. It may also suppress a generic action step when a more specific briefing step already covers the same CI blocker, review concern, or top-ranked file.

Actionable CI titles and descriptions are generated once from structured CI provider, category, state, check name, blocking status, and safe provider description data. Review Actions and Review Briefing reuse that same wording, so a Vercel authorization failure or GitHub Actions test failure is described consistently across report sections without parsing rendered strings.

## Priorities And Categories

Priorities are `high`, `medium`, and `low`.

Categories are `mergeability`, `ci`, `security`, `database`, `testing`, `dependencies`, `configuration`, `infrastructure`, `change_scope`, `code_quality`, `evidence_visibility`, `review`, and `file_review`.

## Rule Groups

Version `v1` includes explicit rules for:

- Merge conflicts, failing CI, credential-like literals, security-control settings, destructive migrations, sensitive changes without test files, and deleted tests.
- Pending CI, CI visibility gaps, migrations without patch visibility, runtime configuration, dependency manifests, infrastructure changes, large change scope, incomplete evidence, and sensitive renames.
- Code-quality hints and generated or opaque changes.
- Review-concern lifecycle prompts for active latest change requests, reviewer follow-ups, conversations awaiting author response, author-described-change responses, and author-claimed-addressed concerns.
- A baseline `action.review_highest_priority_files` action when ranked files exist.

The baseline file-review action includes at most the top five ranked file paths. A file omitted from an action must not be ignored.

## Aggregation And Suppression

MergeSignal emits at most one action per rule for most rule families. Review-concern lifecycle actions are keyed by conversation so separate inline conversations remain individually traceable. It aggregates affected files, related signal IDs, related readiness rule IDs, and safe evidence.

Suppression keeps output concise:

- Failing CI suppresses the pending-CI action.
- Missing, unknown, partial, and unavailable CI produce one CI-visibility action.
- Sensitive-change-without-tests suppresses any future generic production-change-without-tests action.
- Destructive migration and migration-without-patch actions may coexist.
- Credential and security-control actions remain distinct.
- Reviewer follow-ups and active latest change requests take precedence over lower-priority concern states for a conversation.
- Author-described-change actions ask for verification and do not claim the response resolved the concern.
- The baseline file-review action never replaces specific actions.
- The Review Briefing suppresses the baseline file-review action when it emits a specific top-file step for the same canonical path.

Affected files are ordered by ranked-file position when available, then by path case-insensitively, then by original path. In the frontend, actions without explicit paths use scope-aware labels such as `PR-wide`, `CI-wide`, or `Changed-file set` instead of displaying `0 affected files`.

## Security Sanitization

Credential and security-control actions never include suspected secret values, raw patch lines, generated patches, or code replacements. Evidence is summarized from existing sanitized signals and readiness reasons.

## Examples

- Failing CI produces `action.inspect_failing_ci` with provider/category-specific wording when structured CI details are available, such as `Inspect failed GitHub Actions test check`; it falls back to `Inspect failed CI check` only when provider and category are unavailable.
- Pending CI produces provider/category-specific pending-check wording when structured CI details are available.
- Partial CI visibility produces `action.investigate_ci_visibility` with the observed state and visibility.
- A credential-like literal signal produces `action.verify_credential_like_literal` without exposing the suspected value.
- An active latest change request attached to an inline conversation produces `action.review_concern.active_change_request`.
- An author reply that claims a concern was addressed can produce `action.review_concern.verify_author_claim` when no higher-priority concern action applies.
- An author reply that describes concrete changes can produce `action.review_concern.verify_author_response` when no higher-priority concern action applies.
- Ranked files produce `action.review_highest_priority_files` as a review-order summary.

## Limitations

Actions do not prove a defect, do not prove a PR is safe, do not assign reviewers, do not modify code, and do not replace human review. CODEOWNERS and repository policies are not evaluated yet.
