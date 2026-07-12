from app.domain.pull_request import CiState, CiVisibility, PullRequestSnapshot
from app.domain.readiness import DecisionEffect, DecisionReason, MergeReadinessAssessment
from app.domain.review_signal import ReviewSignal
from app.domain.scoring import ConfidenceComponentStatus, EvidenceConfidenceLevel, MergeRiskLevel
from app.readiness.ordering import DECISION_BY_EFFECT, EFFECT_PRECEDENCE, unique_sorted
from app.readiness.rules import READINESS_RULES_VERSION, READY_BASELINE_RULE_ID, RULE_BY_ID, ReadinessRule

READINESS_LIMITATIONS = [
    "A readiness decision is a deterministic heuristic, not proof of correctness.",
    "Ready does not mean safe or bug-free.",
    "Human review remains necessary.",
    "Decisions use only the evidence available in the snapshot.",
]


def calculate_merge_readiness(snapshot: PullRequestSnapshot) -> MergeReadinessAssessment:
    signals_by_rule = _signals_by_rule(snapshot.signals)
    reasons = _evaluate_reasons(snapshot, signals_by_rule)
    if not reasons:
        reasons = [
            _reason(
                READY_BASELINE_RULE_ID,
                observed_value="no_readiness_concerns",
                explanation="No blocking, resolution-required, or caution condition was observed in the available snapshot.",
            )
        ]

    reasons = sorted(reasons, key=_reason_sort_key)
    decisive = reasons[0]
    decision = DECISION_BY_EFFECT[decisive.effect]

    return MergeReadinessAssessment(
        decision=decision,
        decisive_rule_id=decisive.rule_id,
        reasons=reasons,
        blocking_reason_count=sum(1 for reason in reasons if reason.effect == DecisionEffect.BLOCK),
        resolution_reason_count=sum(1 for reason in reasons if reason.effect == DecisionEffect.REQUIRE_RESOLUTION),
        caution_reason_count=sum(1 for reason in reasons if reason.effect == DecisionEffect.CAUTION),
        context_reason_count=sum(1 for reason in reasons if reason.effect == DecisionEffect.CONTEXT),
        rules_version=READINESS_RULES_VERSION,
        limitations=READINESS_LIMITATIONS,
    )


def _evaluate_reasons(
    snapshot: PullRequestSnapshot,
    signals_by_rule: dict[str, list[ReviewSignal]],
) -> list[DecisionReason]:
    reasons: list[DecisionReason] = []

    if "metadata.merge_conflict_observed" in signals_by_rule:
        reasons.append(_signal_reason("readiness.blocked.merge_conflict", signals_by_rule["metadata.merge_conflict_observed"], "merge_conflict_observed"))
    if snapshot.ci.state == CiState.FAILING or "ci.failing" in signals_by_rule:
        reasons.append(_signal_reason("readiness.blocked.ci_failing", signals_by_rule.get("ci.failing", []), snapshot.ci.state.value))

    if snapshot.metadata.draft or "metadata.draft_pull_request" in signals_by_rule:
        reasons.append(_signal_reason("readiness.not_ready.draft", signals_by_rule.get("metadata.draft_pull_request", []), str(snapshot.metadata.draft).lower()))
    if snapshot.ci.state == CiState.PENDING:
        reasons.append(_reason("readiness.not_ready.ci_pending", snapshot.ci.state.value, "The normalized CI state is pending, not failing."))
    if not snapshot.completeness.files_complete:
        reasons.append(_reason("readiness.not_ready.file_collection_incomplete", "files_complete=false", "Changed-file collection is incomplete for this snapshot."))
    if snapshot.ci.visibility == CiVisibility.UNAVAILABLE:
        reasons.append(_reason("readiness.not_ready.ci_unavailable", snapshot.ci.visibility.value, "MergeSignal could not observe either CI surface for the current head SHA."))
    if snapshot.evidence_confidence.level == EvidenceConfidenceLevel.LOW:
        reasons.append(_reason("readiness.not_ready.low_evidence_confidence", snapshot.evidence_confidence.level.value, "Analysis visibility is insufficient for a ready decision, without increasing merge risk."))
    if "security.credential_like_literal_added" in signals_by_rule:
        reasons.append(_signal_reason("readiness.not_ready.credential_like_literal", signals_by_rule["security.credential_like_literal_added"], "credential_like_literal_observed"))
    if "security.security_control_disabled_hint" in signals_by_rule:
        reasons.append(_signal_reason("readiness.not_ready.security_control_disabled", signals_by_rule["security.security_control_disabled_hint"], "security_control_disabled_hint_observed"))
    if snapshot.merge_risk.level == MergeRiskLevel.VERY_HIGH:
        reasons.append(_reason("readiness.not_ready.very_high_risk", snapshot.merge_risk.level.value, "The merge-risk assessment level is very high."))

    if snapshot.merge_risk.level == MergeRiskLevel.HIGH:
        reasons.append(_reason("readiness.caution.high_risk", snapshot.merge_risk.level.value, "The merge-risk assessment level is high."))
    if snapshot.merge_risk.level == MergeRiskLevel.MODERATE:
        reasons.append(_reason("readiness.caution.moderate_risk", snapshot.merge_risk.level.value, "The merge-risk assessment level is moderate."))
    if snapshot.evidence_confidence.level == EvidenceConfidenceLevel.MEDIUM:
        reasons.append(_reason("readiness.caution.medium_evidence_confidence", snapshot.evidence_confidence.level.value, "Evidence confidence is medium for the available snapshot."))
    if snapshot.ci.state == CiState.MISSING and snapshot.ci.visibility == CiVisibility.COMPLETE:
        reasons.append(_reason("readiness.caution.ci_missing", snapshot.ci.state.value, "No CI results were observed for the current head SHA."))
    if snapshot.ci.state == CiState.UNKNOWN and snapshot.ci.visibility != CiVisibility.UNAVAILABLE:
        reasons.append(_signal_reason("readiness.caution.ci_unknown", signals_by_rule.get("ci.unknown_outcome", []), snapshot.ci.state.value))
    if snapshot.ci.visibility == CiVisibility.PARTIAL:
        reasons.append(_signal_reason("readiness.caution.ci_partial_visibility", signals_by_rule.get("ci.partial_visibility", []), snapshot.ci.visibility.value))
    if _component_status(snapshot, "patch_visibility") == ConfidenceComponentStatus.PARTIAL:
        reasons.append(_reason("readiness.caution.patch_visibility_partial", "patch_visibility=partial", "Evidence confidence reports partial patch visibility."))
    if not snapshot.completeness.commits_complete and snapshot.evidence_confidence.level != EvidenceConfidenceLevel.LOW:
        reasons.append(_reason("readiness.caution.commit_collection_incomplete", "commits_complete=false", "Commit collection is incomplete for this snapshot."))
    if "database.destructive_migration_hint" in signals_by_rule:
        reasons.append(_signal_reason("readiness.caution.destructive_migration_hint", signals_by_rule["database.destructive_migration_hint"], "destructive_migration_hint_observed"))
    if "testing.sensitive_change_without_test_files" in signals_by_rule:
        reasons.append(_signal_reason("readiness.caution.sensitive_change_without_tests", signals_by_rule["testing.sensitive_change_without_test_files"], "sensitive_change_without_test_files"))
    if "testing.test_files_deleted" in signals_by_rule:
        reasons.append(_signal_reason("readiness.caution.test_files_deleted", signals_by_rule["testing.test_files_deleted"], "test_files_deleted"))
    if "configuration.runtime_configuration_changed" in signals_by_rule:
        reasons.append(_signal_reason("readiness.caution.runtime_configuration_change", signals_by_rule["configuration.runtime_configuration_changed"], "runtime_configuration_changed"))

    return _deduplicate_reasons(reasons)


def _reason(
    rule_id: str,
    observed_value: str,
    explanation: str,
    *,
    related_signal_ids: list[str] | None = None,
    affected_files: list[str] | None = None,
) -> DecisionReason:
    rule = RULE_BY_ID[rule_id]
    return DecisionReason(
        rule_id=rule.rule_id,
        title=rule.title,
        description=rule.description,
        effect=rule.effect,
        observed_value=observed_value,
        related_signal_ids=unique_sorted(related_signal_ids or []),
        affected_files=unique_sorted(affected_files or []),
        explanation=explanation,
        limitations=list(rule.limitations),
    )


def _signal_reason(rule_id: str, signals: list[ReviewSignal], observed_value: str) -> DecisionReason:
    return _reason(
        rule_id,
        observed_value=observed_value,
        explanation=_signal_explanation(rule_id, observed_value),
        related_signal_ids=[signal.id for signal in signals],
        affected_files=[file for signal in signals for file in signal.affected_files],
    )


def _signal_explanation(rule_id: str, observed_value: str) -> str:
    if rule_id == "readiness.caution.sensitive_change_without_tests":
        return "No test files were changed in this pull request."
    if rule_id == "readiness.blocked.ci_failing":
        return "The observable head-SHA CI surface contains a failing result."
    if rule_id == "readiness.not_ready.credential_like_literal":
        return "A credential-like literal pattern was observed without exposing the suspected value or source line."
    if rule_id == "readiness.not_ready.security_control_disabled":
        return "A security-control disabling pattern was observed without exposing raw patch lines."
    return f"Observed value: {observed_value}."


def _signals_by_rule(signals: list[ReviewSignal]) -> dict[str, list[ReviewSignal]]:
    grouped: dict[str, list[ReviewSignal]] = {}
    for signal in signals:
        grouped.setdefault(signal.rule_id, []).append(signal)
    return {rule_id: sorted(items, key=lambda signal: signal.id) for rule_id, items in grouped.items()}


def _component_status(snapshot: PullRequestSnapshot, component_id: str) -> ConfidenceComponentStatus | None:
    for component in snapshot.evidence_confidence.components:
        if component.id == component_id:
            return component.status
    return None


def _deduplicate_reasons(reasons: list[DecisionReason]) -> list[DecisionReason]:
    by_rule: dict[str, DecisionReason] = {}
    for reason in reasons:
        by_rule.setdefault(reason.rule_id, reason)
    return list(by_rule.values())


def _reason_sort_key(reason: DecisionReason) -> tuple[int, int, str]:
    rule: ReadinessRule = RULE_BY_ID[reason.rule_id]
    return (EFFECT_PRECEDENCE[reason.effect], rule.priority, reason.rule_id)
