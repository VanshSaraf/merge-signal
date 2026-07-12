from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictReadinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MergeReadinessDecision(StrEnum):
    READY = "ready"
    READY_WITH_CAUTION = "ready_with_caution"
    NOT_READY = "not_ready"
    BLOCKED = "blocked"


class DecisionEffect(StrEnum):
    BLOCK = "block"
    REQUIRE_RESOLUTION = "require_resolution"
    CAUTION = "caution"
    CONTEXT = "context"


class DecisionReason(StrictReadinessModel):
    rule_id: str = Field(description="Stable readiness-rule identifier.")
    title: str = Field(description="Short reason title.")
    description: str = Field(description="Deterministic rule description.")
    effect: DecisionEffect = Field(description="Decision effect.")
    observed_value: str = Field(description="Safe observed value.")
    related_signal_ids: list[str] = Field(description="Related review-signal identifiers.")
    affected_files: list[str] = Field(description="Unique affected files in deterministic order.")
    explanation: str = Field(description="Safe explanation for why the rule matched.")
    limitations: list[str] = Field(description="Relevant limitations.")


class MergeReadinessAssessment(StrictReadinessModel):
    decision: MergeReadinessDecision = Field(description="Deterministic merge-readiness decision.")
    decisive_rule_id: str = Field(description="Highest-precedence rule that determined the decision.")
    reasons: list[DecisionReason] = Field(description="Structured decision reasons.")
    blocking_reason_count: int = Field(ge=0, description="Number of blocking reasons.")
    resolution_reason_count: int = Field(ge=0, description="Number of resolution-required reasons.")
    caution_reason_count: int = Field(ge=0, description="Number of caution reasons.")
    context_reason_count: int = Field(ge=0, description="Number of context reasons.")
    rules_version: str = Field(description="Readiness rules version.")
    limitations: list[str] = Field(description="Assessment limitations.")

    @model_validator(mode="after")
    def validate_counts_and_decision(self) -> "MergeReadinessAssessment":
        if not self.decisive_rule_id:
            raise ValueError("decisive_rule_id is required")
        counts = {
            DecisionEffect.BLOCK: self.blocking_reason_count,
            DecisionEffect.REQUIRE_RESOLUTION: self.resolution_reason_count,
            DecisionEffect.CAUTION: self.caution_reason_count,
            DecisionEffect.CONTEXT: self.context_reason_count,
        }
        for effect, expected_count in counts.items():
            actual_count = sum(1 for reason in self.reasons if reason.effect == effect)
            if actual_count != expected_count:
                raise ValueError(f"{effect.value} reason count does not match reasons")
        if not any(reason.rule_id == self.decisive_rule_id for reason in self.reasons):
            raise ValueError("decisive_rule_id must identify one reason")
        return self
