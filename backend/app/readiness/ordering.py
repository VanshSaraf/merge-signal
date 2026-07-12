from types import MappingProxyType

from app.domain.readiness import DecisionEffect, MergeReadinessDecision

EFFECT_PRECEDENCE = MappingProxyType({
    DecisionEffect.BLOCK: 0,
    DecisionEffect.REQUIRE_RESOLUTION: 1,
    DecisionEffect.CAUTION: 2,
    DecisionEffect.CONTEXT: 3,
})

DECISION_BY_EFFECT = MappingProxyType({
    DecisionEffect.BLOCK: MergeReadinessDecision.BLOCKED,
    DecisionEffect.REQUIRE_RESOLUTION: MergeReadinessDecision.NOT_READY,
    DecisionEffect.CAUTION: MergeReadinessDecision.READY_WITH_CAUTION,
    DecisionEffect.CONTEXT: MergeReadinessDecision.READY,
})


def unique_sorted(values: list[str] | tuple[str, ...]) -> list[str]:
    return sorted(set(values), key=lambda value: (value.casefold(), value))
