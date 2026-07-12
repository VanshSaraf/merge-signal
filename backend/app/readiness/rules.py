from dataclasses import dataclass
from types import MappingProxyType

from app.domain.readiness import DecisionEffect

READINESS_RULES_VERSION = "v1"
READY_BASELINE_RULE_ID = "readiness.ready_baseline"


@dataclass(frozen=True)
class ReadinessRule:
    rule_id: str
    title: str
    description: str
    effect: DecisionEffect
    limitations: tuple[str, ...]
    priority: int


RULES: tuple[ReadinessRule, ...] = (
    ReadinessRule(
        "readiness.blocked.merge_conflict",
        "GitHub reports a merge conflict condition",
        "An existing review signal reports a GitHub merge conflict condition.",
        DecisionEffect.BLOCK,
        ("GitHub mergeability may be temporarily unavailable or recomputed.",),
        10,
    ),
    ReadinessRule(
        "readiness.blocked.ci_failing",
        "CI is currently failing",
        "The observable head-SHA CI surface contains a failing result.",
        DecisionEffect.BLOCK,
        ("This does not infer which checks are required by repository policy.",),
        20,
    ),
    ReadinessRule(
        "readiness.not_ready.draft",
        "Pull request is marked as draft",
        "Pull-request metadata or review signals indicate draft status.",
        DecisionEffect.REQUIRE_RESOLUTION,
        ("Draft status is contextual and does not describe code correctness.",),
        110,
    ),
    ReadinessRule(
        "readiness.not_ready.ci_pending",
        "CI is still pending",
        "The normalized CI state is pending for the current head SHA.",
        DecisionEffect.REQUIRE_RESOLUTION,
        ("Pending CI may change after the snapshot is collected.",),
        120,
    ),
    ReadinessRule(
        "readiness.not_ready.file_collection_incomplete",
        "Changed-file collection is incomplete",
        "Snapshot completeness reports that changed-file collection is incomplete.",
        DecisionEffect.REQUIRE_RESOLUTION,
        ("Signal detection only covers retrieved files.",),
        130,
    ),
    ReadinessRule(
        "readiness.not_ready.ci_unavailable",
        "CI visibility is unavailable",
        "MergeSignal cannot observe the head-SHA CI surface.",
        DecisionEffect.REQUIRE_RESOLUTION,
        ("Unavailable CI visibility does not imply CI is absent.",),
        140,
    ),
    ReadinessRule(
        "readiness.not_ready.low_evidence_confidence",
        "Evidence confidence is low",
        "Evidence confidence is low, limiting a ready decision from the available snapshot.",
        DecisionEffect.REQUIRE_RESOLUTION,
        ("Evidence confidence describes visibility, not code quality.",),
        150,
    ),
    ReadinessRule(
        "readiness.not_ready.credential_like_literal",
        "A credential-like literal pattern was observed",
        "An existing review signal reports a credential-like literal pattern.",
        DecisionEffect.REQUIRE_RESOLUTION,
        ("The heuristic does not confirm that the value is active, valid, or sensitive.",),
        160,
    ),
    ReadinessRule(
        "readiness.not_ready.security_control_disabled",
        "A security-control disabling pattern was observed",
        "An existing review signal reports a security-control disabling pattern.",
        DecisionEffect.REQUIRE_RESOLUTION,
        ("The pattern is heuristic and requires human verification.",),
        170,
    ),
    ReadinessRule(
        "readiness.not_ready.very_high_risk",
        "Merge risk is very high",
        "The merge-risk assessment level is very high.",
        DecisionEffect.REQUIRE_RESOLUTION,
        ("The score is a deterministic review heuristic and does not prove a defect.",),
        180,
    ),
    ReadinessRule(
        "readiness.caution.high_risk",
        "Merge risk is high",
        "The merge-risk assessment level is high.",
        DecisionEffect.CAUTION,
        ("The score is a deterministic review heuristic and does not prove a defect.",),
        310,
    ),
    ReadinessRule(
        "readiness.caution.moderate_risk",
        "Merge risk is moderate",
        "The merge-risk assessment level is moderate.",
        DecisionEffect.CAUTION,
        ("The score is a deterministic review heuristic and does not prove a defect.",),
        320,
    ),
    ReadinessRule(
        "readiness.caution.medium_evidence_confidence",
        "Evidence confidence is medium",
        "Evidence confidence is medium for the available snapshot.",
        DecisionEffect.CAUTION,
        ("Evidence confidence describes visibility, not code quality.",),
        330,
    ),
    ReadinessRule(
        "readiness.caution.ci_missing",
        "No CI results were observed for the current head SHA",
        "CI visibility is complete and no CI records were observed for the current head SHA.",
        DecisionEffect.CAUTION,
        ("This does not claim the repository lacks CI configuration.",),
        340,
    ),
    ReadinessRule(
        "readiness.caution.ci_unknown",
        "CI outcome could not be classified",
        "Observed CI records contain states or conclusions not classified by the current CI model.",
        DecisionEffect.CAUTION,
        ("Unknown CI state is not interpreted as passing or failing.",),
        350,
    ),
    ReadinessRule(
        "readiness.caution.ci_partial_visibility",
        "CI visibility is partial",
        "MergeSignal observed only part of the CI surface for the current head SHA.",
        DecisionEffect.CAUTION,
        ("Partial CI visibility can omit relevant check or status records.",),
        360,
    ),
    ReadinessRule(
        "readiness.caution.patch_visibility_partial",
        "Patch visibility is partial",
        "Evidence confidence reports partial patch visibility.",
        DecisionEffect.CAUTION,
        ("Patch-based signals may be incomplete for eligible files without patch text.",),
        370,
    ),
    ReadinessRule(
        "readiness.caution.commit_collection_incomplete",
        "Commit collection is incomplete",
        "Snapshot completeness reports that commit collection is incomplete.",
        DecisionEffect.CAUTION,
        ("Commit-derived signals only cover retrieved commit metadata.",),
        380,
    ),
    ReadinessRule(
        "readiness.caution.destructive_migration_hint",
        "A destructive migration pattern was observed",
        "An existing review signal reports a destructive migration pattern.",
        DecisionEffect.CAUTION,
        ("This heuristic does not determine whether the migration is safe or unsafe.",),
        390,
    ),
    ReadinessRule(
        "readiness.caution.sensitive_change_without_tests",
        "Sensitive-area changes were observed without changed test files",
        "No test files were changed in this pull request.",
        DecisionEffect.CAUTION,
        ("This does not prove test coverage is absent.",),
        400,
    ),
    ReadinessRule(
        "readiness.caution.test_files_deleted",
        "Test files were deleted",
        "An existing review signal reports deleted test files.",
        DecisionEffect.CAUTION,
        ("Removing a test file may be intentional and is not a correctness claim.",),
        410,
    ),
    ReadinessRule(
        "readiness.caution.runtime_configuration_change",
        "Runtime configuration changed",
        "An existing review signal reports runtime configuration path changes.",
        DecisionEffect.CAUTION,
        ("Configuration path matching does not prove runtime behavior changed.",),
        420,
    ),
    ReadinessRule(
        READY_BASELINE_RULE_ID,
        "No readiness concerns observed",
        "No blocking, resolution-required, or caution condition was observed in the available snapshot.",
        DecisionEffect.CONTEXT,
        ("Ready does not prove correctness or safety.",),
        900,
    ),
)

RULE_BY_ID = MappingProxyType({rule.rule_id: rule for rule in RULES})
