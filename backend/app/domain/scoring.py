from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.review_signal import SignalSeverity


class StrictScoringModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MergeRiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class EvidenceConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskGroup(StrEnum):
    CHANGE_SCOPE = "change_scope"
    SENSITIVE_SYSTEMS = "sensitive_systems"
    TESTING = "testing"
    CI = "ci"
    OPERATIONAL_CHANGE = "operational_change"
    CODE_QUALITY = "code_quality"


class ConfidenceComponentStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class RiskContribution(StrictScoringModel):
    signal_id: str = Field(description="Deterministic source signal identifier.")
    rule_id: str = Field(description="Review-signal rule identifier.")
    group: RiskGroup = Field(description="Risk group receiving this contribution.")
    title: str = Field(description="Observed signal title.")
    severity: SignalSeverity = Field(description="Observed signal severity.")
    raw_points: int = Field(ge=0, description="Configured risk points before group caps.")
    applied_points: int = Field(ge=0, description="Risk points applied after group caps.")
    capped: bool = Field(description="Whether any configured points were excluded by a group cap.")
    affected_files: list[str] = Field(description="Unique affected files in deterministic order.")
    explanation: str = Field(description="Safe explanation for the risk contribution.")

    @model_validator(mode="after")
    def validate_applied_points(self) -> "RiskContribution":
        if self.applied_points > self.raw_points:
            raise ValueError("applied_points cannot exceed raw_points")
        if self.capped != (self.applied_points < self.raw_points):
            raise ValueError("capped must reflect whether applied_points is below raw_points")
        return self


class RiskGroupScore(StrictScoringModel):
    group: RiskGroup = Field(description="Risk group.")
    raw_points: int = Field(ge=0, description="Raw configured points in this group.")
    applied_points: int = Field(ge=0, description="Applied points after the group cap.")
    cap: int = Field(ge=0, description="Maximum applied points for this group.")
    capped_points: int = Field(ge=0, description="Raw points excluded by the cap.")
    contribution_count: int = Field(ge=0, description="Number of nonzero configured contributions.")

    @model_validator(mode="after")
    def validate_group_points(self) -> "RiskGroupScore":
        if self.applied_points > self.cap:
            raise ValueError("applied_points cannot exceed cap")
        if self.capped_points != self.raw_points - self.applied_points:
            raise ValueError("capped_points must equal raw_points minus applied_points")
        return self


class MergeRiskAssessment(StrictScoringModel):
    score: int = Field(ge=0, le=100, description="Merge risk score.")
    level: MergeRiskLevel = Field(description="Merge risk level.")
    max_score: int = Field(default=100, description="Maximum merge risk score.")
    group_scores: list[RiskGroupScore] = Field(description="Risk group score breakdown.")
    contributions: list[RiskContribution] = Field(description="Applied and capped risk contributions.")
    contributing_signal_count: int = Field(ge=0, description="Signals with nonzero configured risk weight.")
    non_scoring_signal_count: int = Field(ge=0, description="Signals with zero or no configured risk weight.")
    rules_version: str = Field(description="Scoring rules version.")
    limitations: list[str] = Field(description="Deterministic analysis limitations.")

    @model_validator(mode="after")
    def validate_assessment(self) -> "MergeRiskAssessment":
        if self.max_score != 100:
            raise ValueError("max_score must equal 100")
        if sum(group.applied_points for group in self.group_scores) != self.score:
            raise ValueError("score must equal the sum of applied group points")
        if sum(group.cap for group in self.group_scores) != 100:
            raise ValueError("risk group caps must total 100")
        if self.contributing_signal_count != len(self.contributions):
            raise ValueError("contributing_signal_count must equal contribution count")
        return self


class ConfidenceComponent(StrictScoringModel):
    id: str = Field(description="Stable component identifier.")
    name: str = Field(description="Display name.")
    maximum_points: int = Field(ge=0, description="Maximum component points.")
    awarded_points: int = Field(ge=0, description="Awarded component points.")
    status: ConfidenceComponentStatus = Field(description="Visibility status.")
    explanation: str = Field(description="Explanation for awarded points.")
    limitations: list[str] = Field(description="Component limitations.")

    @model_validator(mode="after")
    def validate_awarded_points(self) -> "ConfidenceComponent":
        if self.awarded_points > self.maximum_points:
            raise ValueError("awarded_points cannot exceed maximum_points")
        return self


class EvidenceConfidenceAssessment(StrictScoringModel):
    score: int = Field(ge=0, le=100, description="Evidence confidence score.")
    level: EvidenceConfidenceLevel = Field(description="Evidence confidence level.")
    max_score: int = Field(default=100, description="Maximum evidence confidence score.")
    components: list[ConfidenceComponent] = Field(description="Confidence component breakdown.")
    warnings: list[str] = Field(description="Deterministic visibility warnings.")
    rules_version: str = Field(description="Scoring rules version.")
    limitations: list[str] = Field(description="Deterministic confidence limitations.")

    @model_validator(mode="after")
    def validate_assessment(self) -> "EvidenceConfidenceAssessment":
        if self.max_score != 100:
            raise ValueError("max_score must equal 100")
        if sum(component.awarded_points for component in self.components) != self.score:
            raise ValueError("score must equal the sum of awarded component points")
        if sum(component.maximum_points for component in self.components) != 100:
            raise ValueError("confidence component maximums must total 100")
        return self
