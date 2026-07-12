from dataclasses import dataclass
from types import MappingProxyType

from app.domain.review_action import ReviewActionCategory, ReviewActionPriority

REVIEW_ACTION_RULES_VERSION = "v1"


@dataclass(frozen=True)
class ReviewActionRule:
    rule_id: str
    title: str
    description: str
    priority: ReviewActionPriority
    category: ReviewActionCategory
    limitations: tuple[str, ...]


RULES: tuple[ReviewActionRule, ...] = (
    ReviewActionRule("action.resolve_merge_conflict", "Resolve merge conflict", "Verify the merge-conflict condition before merge readiness can be restored.", ReviewActionPriority.HIGH, ReviewActionCategory.MERGEABILITY, ("GitHub mergeability may be recomputed by GitHub.",)),
    ReviewActionRule("action.inspect_failing_ci", "Inspect failing CI", "Review the observable failing CI state for the current head SHA.", ReviewActionPriority.HIGH, ReviewActionCategory.CI, ("MergeSignal does not infer which checks are required.",)),
    ReviewActionRule("action.verify_credential_like_literal", "Verify credential-like literal", "Check whether the credential-like literal signal is intentional and safe without exposing the suspected value.", ReviewActionPriority.HIGH, ReviewActionCategory.SECURITY, ("The heuristic does not prove the value is valid, active, or sensitive.",)),
    ReviewActionRule("action.verify_security_control_setting", "Verify security-control setting", "Check whether the security-control disabling signal is intentional and safe.", ReviewActionPriority.HIGH, ReviewActionCategory.SECURITY, ("The heuristic does not determine runtime reachability or intent.",)),
    ReviewActionRule("action.inspect_destructive_migration", "Inspect destructive migration", "Review the destructive migration signal and its affected migration files.", ReviewActionPriority.HIGH, ReviewActionCategory.DATABASE, ("The heuristic does not determine whether the migration is safe or unsafe.",)),
    ReviewActionRule("action.review_sensitive_change_tests", "Review sensitive change test evidence", "Check sensitive changed files with the context that no test files changed in this PR.", ReviewActionPriority.HIGH, ReviewActionCategory.TESTING, ("This does not prove test coverage is absent.",)),
    ReviewActionRule("action.review_deleted_tests", "Review deleted tests", "Review deleted test files and the surrounding PR context.", ReviewActionPriority.HIGH, ReviewActionCategory.TESTING, ("Removing a test file may be intentional.",)),
    ReviewActionRule("action.await_pending_ci", "Await pending CI", "Wait for or inspect the pending CI state for the current head SHA.", ReviewActionPriority.MEDIUM, ReviewActionCategory.CI, ("Pending CI may change after this snapshot.",)),
    ReviewActionRule("action.investigate_ci_visibility", "Investigate CI visibility", "Review the observed CI visibility or unknown CI outcome state.", ReviewActionPriority.MEDIUM, ReviewActionCategory.CI, ("Unavailable or partial CI visibility can omit relevant records.",)),
    ReviewActionRule("action.inspect_migration_without_patch", "Inspect migration without patch visibility", "Review migration files whose patch-level inspection was unavailable.", ReviewActionPriority.MEDIUM, ReviewActionCategory.DATABASE, ("This is a visibility action, not a migration-correctness claim.",)),
    ReviewActionRule("action.review_runtime_configuration", "Review runtime configuration", "Review runtime configuration files changed by this PR.", ReviewActionPriority.MEDIUM, ReviewActionCategory.CONFIGURATION, ("Configuration path matching does not prove runtime behavior changed.",)),
    ReviewActionRule("action.review_dependency_manifest", "Review dependency manifest", "Review dependency manifest changes and any missing companion lockfile evidence.", ReviewActionPriority.MEDIUM, ReviewActionCategory.DEPENDENCIES, ("Manifest conventions are conservative and may not apply to every repository.",)),
    ReviewActionRule("action.review_infrastructure_change", "Review infrastructure change", "Review infrastructure or deployment configuration changes.", ReviewActionPriority.MEDIUM, ReviewActionCategory.INFRASTRUCTURE, ("Infrastructure classification is path-based.",)),
    ReviewActionRule("action.review_large_change_scope", "Review large change scope", "Review the large or broad change-scope signals for this PR.", ReviewActionPriority.MEDIUM, ReviewActionCategory.CHANGE_SCOPE, ("Size and breadth do not prove implementation risk.",)),
    ReviewActionRule("action.inspect_incomplete_evidence", "Inspect incomplete evidence", "Review incomplete file, commit, or patch evidence before relying on the snapshot.", ReviewActionPriority.MEDIUM, ReviewActionCategory.EVIDENCE_VISIBILITY, ("Incomplete evidence can omit relevant context.",)),
    ReviewActionRule("action.review_sensitive_rename", "Review sensitive rename", "Review rename transitions into sensitive areas or out of test classification.", ReviewActionPriority.MEDIUM, ReviewActionCategory.FILE_REVIEW, ("Rename classification does not infer intent.",)),
    ReviewActionRule("action.review_code_quality_hints", "Review code-quality hints", "Review aggregated code-quality signals such as debug statements, TODO/FIXME markers, suppressions, or empty exception handlers.", ReviewActionPriority.LOW, ReviewActionCategory.CODE_QUALITY, ("Line-based hints do not parse complete source files.",)),
    ReviewActionRule("action.review_generated_or_opaque_changes", "Review generated or opaque changes", "Review generated, large generated, opaque, or patchless changed files.", ReviewActionPriority.LOW, ReviewActionCategory.EVIDENCE_VISIBILITY, ("Generated or opaque changes may be expected outputs.",)),
    ReviewActionRule("action.review_highest_priority_files", "Review highest-priority files", "Use the highest-ranked changed files as a review-order starting point.", ReviewActionPriority.LOW, ReviewActionCategory.FILE_REVIEW, ("A file omitted from this action must not be ignored.",)),
)

RULE_BY_ID = MappingProxyType({rule.rule_id: rule for rule in RULES})
