# File Prioritization

MergeSignal ranks changed files by deterministic review priority after classification, review signals, merge risk, evidence confidence, and merge readiness are available.

File priority is not merge risk. Merge risk describes pull-request-level risk signals; file priority orders changed files for review attention. A high-priority file is not proven defective, and a low-priority file must not be ignored. Ranking does not replace human review.

## Output

Snapshot responses include:

- `ranked_files`: every changed file exactly once, ordered by deterministic review priority.
- `file_priority_summary`: counts by priority level, up to ten highest-priority paths, visibility counts, signal-factor counts, rule version, and limitations.

Each ranked file includes current path, previous path for renames, status, score, level, classification fields, path context, change magnitude, line counts, related signal IDs, applied factors, and limitations.

## Levels

Scores are bounded from 0 to 100.

- `low`: 0-19
- `medium`: 20-39
- `high`: 40-69
- `very_high`: 70-100

## Factor Groups

Version `v1` uses capped factor groups:

- `review_attention`: capped at 25 points. Current inline review conversations can contribute when they show reviewer follow-up, active latest change requests, awaiting author response, or author-claimed-addressed verification needs. Outdated conversations do not contribute by themselves.
- `signal_impact`: capped at 50 points. Only signals whose `affected_files` explicitly contain the current file path can contribute. PR-level metadata and CI signals are not assigned to every file.
- `file_context`: capped at 25 points. Admin surfaces, protected route groups, route pages, dynamic routes, and user-facing route conventions can contribute.
- `sensitive_area`: capped at 25 points. Security, authentication, authorization, database, infrastructure, CI/CD, API, runtime configuration, and database migration classifications can contribute.
- `change_size`: capped at 15 points. Changed-line magnitude uses additions plus deletions.
- `visibility`: capped at 5 points. Patch-eligible files with missing patches, binary files, opaque generated files, and truncation warnings can contribute. Assets are not penalized merely because GitHub omits patch text.
- `rename_transition`: capped at 5 points. Moving into sensitive areas, moving out of test classification, or moving into generated classification can contribute.

Unknown signal rule IDs contribute zero points. Signal IDs are deduplicated.

Scores remain globally bounded to 100 even though group caps are independent.

## Change Magnitude

Magnitude bands are deterministic:

- `tiny`: 0-19 changed lines
- `small`: 20-99 changed lines
- `medium`: 100-299 changed lines
- `large`: 300-999 changed lines
- `very_large`: 1000+ changed lines

Deletions and additions are both counted. Missing line counts fall back to the normalized additions plus deletions already provided in the changed-file model.

## Contributions

Each priority factor includes a stable ID, category, applied points, human-readable explanation, related signal IDs, related review-thread IDs when applicable, evidence, and observed value. Factors are sorted deterministically by group order, points, rule ID, and observed value.

The final file score is the sum of applied factor points after group caps, bounded to 100. Contribution totals are expected to match the final score.

Review-concern factors use only already-collected review-context evidence. Author-claimed-addressed concerns add verification weight; they are not treated as resolved. Global CI failures do not inflate every file unless a file-specific relationship is observable.

## Ordering

Files are ordered by score descending, priority level descending, changed-line count descending, current path case-insensitively, then current path. Ranks are stable and 1-based.

## Non-Goals

File prioritization does not provide recommendations, reviewer suggestions, CODEOWNERS evaluation, repository policy evaluation, automatic code modification, generated fixes, or generic AI code-review commentary.

## Review Actions

Review actions are built after file prioritization. The baseline file-review action may include the top five ranked files as a review-order summary, but it must not claim that omitted or lower-ranked files can be ignored. See [Review actions](review-actions.md).
