from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictSignalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SignalSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SignalCategory(StrEnum):
    METADATA = "metadata"
    CHANGE_SCOPE = "change_scope"
    TESTING = "testing"
    CI = "ci"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATABASE = "database"
    DEPENDENCIES = "dependencies"
    API = "api"
    INFRASTRUCTURE = "infrastructure"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    CODE_QUALITY = "code_quality"
    GENERATED_CONTENT = "generated_content"
    RENAME = "rename"
    COMPLETENESS = "completeness"


class SignalScope(StrEnum):
    PULL_REQUEST = "pull_request"
    FILE_SET = "file_set"
    FILE = "file"
    CI_SURFACE = "ci_surface"
    SNAPSHOT = "snapshot"


class EvidenceKind(StrEnum):
    METADATA = "metadata"
    FILE_PATH = "file_path"
    FILE_COUNT = "file_count"
    LINE_COUNT = "line_count"
    CLASSIFICATION = "classification"
    CI_STATE = "ci_state"
    CI_VISIBILITY = "ci_visibility"
    PATCH_PATTERN = "patch_pattern"
    RENAME_TRANSITION = "rename_transition"
    COMPLETENESS = "completeness"
    COMMIT_COUNT = "commit_count"


class SignalEvidence(StrictSignalModel):
    kind: EvidenceKind = Field(description="Structured evidence kind.")
    message: str = Field(description="Safe display message for the observed condition.")
    file: str | None = Field(default=None, description="Affected repository path when applicable.")
    observed_value: str | None = Field(default=None, description="Sanitized observed value.")
    expected_context: str | None = Field(default=None, description="Expected or comparison context.")


class ReviewSignal(StrictSignalModel):
    id: str = Field(description="Deterministic signal identifier.")
    rule_id: str = Field(description="Stable rule identifier.")
    title: str = Field(description="Short signal title.")
    description: str = Field(description="Conservative explanation of the observed pattern.")
    category: SignalCategory = Field(description="Primary signal category.")
    severity: SignalSeverity = Field(description="Deterministic severity.")
    scope: SignalScope = Field(description="Signal scope.")
    affected_files: list[str] = Field(description="Unique affected files in deterministic order.")
    evidence: list[SignalEvidence] = Field(description="Deduplicated evidence in deterministic order.")
    limitations: list[str] = Field(description="Relevant uncertainty and scope limitations.")
    tags: list[str] = Field(description="Stable lowercase tags.")


class SignalCount(StrictSignalModel):
    name: str = Field(description="Enum value.")
    count: int = Field(ge=0, description="Number of signals with this value.")


class ReviewSignalSummary(StrictSignalModel):
    total_signals: int = Field(ge=0, description="Total emitted review signals.")
    counts_by_severity: list[SignalCount] = Field(description="Counts by signal severity.")
    counts_by_category: list[SignalCount] = Field(description="Counts by signal category.")
    files_with_signals: list[str] = Field(description="Files affected by one or more signals.")
    high_attention_files: list[str] = Field(description="Files affected by one or more high-severity signals.")
    patch_based_signal_count: int = Field(ge=0, description="Signals derived from patch content.")
    metadata_signal_count: int = Field(ge=0, description="Signals derived from pull-request metadata.")
    ci_signal_count: int = Field(ge=0, description="Signals derived from CI state or visibility.")
    warnings: list[str] = Field(description="Deduplicated signal-engine warnings.")
    rules_version: str = Field(description="Stable signal-rule version.")


class SignalDetectionResult(StrictSignalModel):
    signals: list[ReviewSignal] = Field(description="Detected review signals.")
    summary: ReviewSignalSummary = Field(description="Review-signal summary.")
