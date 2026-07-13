# Review Briefing

The Review Briefing is a deterministic reviewer workflow derived from the current pull-request snapshot. It is additive: it does not change merge risk, evidence confidence, merge readiness, review actions, file priority, or review-context lifecycle.

## Input Sources

The briefing uses only already-normalized snapshot evidence:

- merge-readiness decision and reasons
- CI explanation surfaces and blocking items
- review-concern lifecycle states
- review signals
- review actions
- ranked files and file-context factors
- evidence-confidence score and visibility gaps

It does not call GitHub, parse PR descriptions, inspect code semantically, use AI commentary, clone repositories, execute code, or install dependencies.

## Output Fields

`review_briefing` includes:

- `status`, `headline`, and `summary`
- `primary_reason`
- up to three `review_focus` items
- up to three `priority_files`
- up to five `recommended_steps`
- copyable `checklist` lines
- up to three relevant `limitations`
- `provenance` grouped by readiness, CI, signal, action, file, and review-thread identifiers

Every item must be traceable to current snapshot evidence.

## Precedence

Focus items are ordered by deterministic precedence:

1. hard readiness blockers
2. specific blocking CI surfaces
3. active latest change requests
4. reviewer follow-ups
5. conversations awaiting author response
6. author-claimed-addressed concerns requiring reviewer verification
7. high review signals
8. materially incomplete evidence
9. highest-priority files
10. production changes without test-file changes through existing actions
11. lower-priority reviewer guidance

The implementation deduplicates related evidence so a failing CI readiness reason, specific CI blocking item, CI signal, and CI action normally become one focus item. CI deduplication uses a canonical evidence identity derived from source type, normalized provider, normalized check or context name, and the safe details URL when present. Distinct failing checks keep distinct identities and remain separate.

## Headlines

Headlines use the current readiness status and the strongest traceable reason. CI headlines identify the observed failing surface when available, such as a provider-specific deployment or test check. Headlines never claim a PR is safe, bug-free, approved, or fully resolved.

## Checklist

Checklist output is stable plain text with up to five non-overlapping reviewer actions:

```text
[ ] Inspect failed deployment check
[ ] Review the latest reviewer follow-up
```

Checklist lines suppress generic CI wording when a more specific CI blocker exists. They avoid raw patches, comment technical IDs, credentials, and unsupported claims.

## Safe Links

The briefing uses only safe existing or derivable links:

- CI details URLs already normalized by CI explanation
- review conversation URLs already normalized by review context
- GitHub file URLs derived from owner, repository, head SHA, and URL-encoded path
- pull-request URL when already present

Links are omitted when unsafe, incomplete, non-HTTPS, or credential-bearing.

## Limitations

The briefing is deterministic workflow guidance, not semantic code review. It does not prove correctness, verify author-claimed fixes, infer formal review-thread resolution, or expand evidence confidence beyond collected sources.
