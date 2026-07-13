from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.file_classification import ChangeMagnitude, FileArea, FileContext, FileKind, FileLanguage


class StrictFilePriorityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FilePriorityLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class FilePriorityFactor(StrictFilePriorityModel):
    id: str = Field(description="Stable factor identifier.")
    category: str = Field(description="Factor category.")
    points: int = Field(ge=0, description="Applied factor points after group caps.")
    description: str = Field(description="Safe factor explanation.")
    related_signal_ids: list[str] = Field(description="Related signal identifiers.")
    related_thread_ids: list[str] = Field(default_factory=list, description="Related review-thread identifiers.")
    evidence: list[str] = Field(default_factory=list, description="Safe observable evidence for this factor.")
    observed_value: str | None = Field(default=None, description="Safe observed value.")


class RankedFile(StrictFilePriorityModel):
    rank: int = Field(ge=1, description="Stable 1-based review-priority rank.")
    path: str = Field(description="Current changed-file path.")
    previous_path: str | None = Field(description="Previous path for renamed files.")
    status: str = Field(description="GitHub file status.")
    score: int = Field(ge=0, le=100, description="Deterministic file-priority score.")
    level: FilePriorityLevel = Field(description="File-priority level.")
    primary_kind: FileKind = Field(description="Classified primary file kind.")
    areas: list[FileArea] = Field(description="Classified file areas.")
    language: FileLanguage = Field(description="Classified language.")
    context: FileContext = Field(default_factory=FileContext, description="Path-derived file context.")
    change_magnitude: ChangeMagnitude = Field(default=ChangeMagnitude.TINY, description="Changed-line magnitude band.")
    changes: int = Field(ge=0, description="Changed-line count.")
    additions: int = Field(ge=0, description="Line additions.")
    deletions: int = Field(ge=0, description="Line deletions.")
    related_signal_ids: list[str] = Field(description="Deduplicated related signal identifiers.")
    factors: list[FilePriorityFactor] = Field(description="Applied priority factors.")
    limitations: list[str] = Field(description="File-priority limitations.")


class FilePriorityCount(StrictFilePriorityModel):
    name: str = Field(description="Priority level value.")
    count: int = Field(ge=0, description="Number of files at this level.")


class FilePrioritySummary(StrictFilePriorityModel):
    total_files: int = Field(ge=0, description="Total ranked files.")
    counts_by_level: list[FilePriorityCount] = Field(description="Counts by priority level.")
    highest_priority_files: list[str] = Field(description="At most ten highest-priority paths.")
    files_with_signal_factors: int = Field(ge=0, description="Files with signal-impact factors.")
    files_with_limited_patch_visibility: int = Field(ge=0, description="Files with limited patch visibility factors.")
    rules_version: str = Field(description="File-priority rules version.")
    limitations: list[str] = Field(description="Summary limitations.")

    @model_validator(mode="after")
    def validate_summary_counts(self) -> "FilePrioritySummary":
        if sum(count.count for count in self.counts_by_level) != self.total_files:
            raise ValueError("counts_by_level must sum to total_files")
        if len(self.highest_priority_files) > 10:
            raise ValueError("highest_priority_files cannot contain more than 10 paths")
        return self
