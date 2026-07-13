from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictReviewActionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReviewActionPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewActionCategory(StrEnum):
    MERGEABILITY = "mergeability"
    CI = "ci"
    SECURITY = "security"
    DATABASE = "database"
    TESTING = "testing"
    DEPENDENCIES = "dependencies"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"
    CHANGE_SCOPE = "change_scope"
    CODE_QUALITY = "code_quality"
    EVIDENCE_VISIBILITY = "evidence_visibility"
    FILE_REVIEW = "file_review"
    REVIEW = "review"


class ReviewAction(StrictReviewActionModel):
    id: str = Field(description="Stable action identifier.")
    rule_id: str = Field(description="Stable action-rule identifier.")
    title: str = Field(description="Short review prompt title.")
    description: str = Field(description="Deterministic review prompt.")
    priority: ReviewActionPriority = Field(description="Review action priority.")
    category: ReviewActionCategory = Field(description="Review action category.")
    affected_files: list[str] = Field(description="Affected files in deterministic order.")
    related_signal_ids: list[str] = Field(description="Related review-signal identifiers.")
    related_readiness_rule_ids: list[str] = Field(description="Related readiness-rule identifiers.")
    evidence: list[str] = Field(description="Safe evidence summaries.")
    limitations: list[str] = Field(description="Relevant limitations.")


class ReviewActionCount(StrictReviewActionModel):
    name: str = Field(description="Enum value.")
    count: int = Field(ge=0, description="Number of actions with this value.")


class ReviewActionSummary(StrictReviewActionModel):
    total_actions: int = Field(ge=0, description="Total emitted review actions.")
    counts_by_priority: list[ReviewActionCount] = Field(description="Counts by priority.")
    counts_by_category: list[ReviewActionCount] = Field(description="Counts by category.")
    affected_file_count: int = Field(ge=0, description="Number of files referenced by actions.")
    high_priority_action_count: int = Field(ge=0, description="Number of high-priority actions.")
    rules_version: str = Field(description="Review-action rules version.")
    limitations: list[str] = Field(description="Summary limitations.")

    @model_validator(mode="after")
    def validate_summary_counts(self) -> "ReviewActionSummary":
        if sum(count.count for count in self.counts_by_priority) != self.total_actions:
            raise ValueError("counts_by_priority must sum to total_actions")
        if sum(count.count for count in self.counts_by_category) != self.total_actions:
            raise ValueError("counts_by_category must sum to total_actions")
        return self
