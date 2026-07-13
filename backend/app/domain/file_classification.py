from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictClassificationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileKind(StrEnum):
    SOURCE = "source"
    TEST = "test"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    DEPENDENCY_MANIFEST = "dependency_manifest"
    DEPENDENCY_LOCKFILE = "dependency_lockfile"
    DATABASE_MIGRATION = "database_migration"
    CI_CONFIGURATION = "ci_configuration"
    INFRASTRUCTURE = "infrastructure"
    GENERATED = "generated"
    ASSET = "asset"
    BINARY = "binary"
    UNKNOWN = "unknown"


class FileArea(StrEnum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    API = "api"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATABASE = "database"
    DEPENDENCIES = "dependencies"
    CI_CD = "ci_cd"
    INFRASTRUCTURE = "infrastructure"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    GENERATED = "generated"
    SECURITY = "security"
    BUILD_TOOLING = "build_tooling"


class FileLanguage(StrEnum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"
    KOTLIN = "kotlin"
    SWIFT = "swift"
    SCALA = "scala"
    SQL = "sql"
    SHELL = "shell"
    POWERSHELL = "powershell"
    HTML = "html"
    CSS = "css"
    SCSS = "scss"
    LESS = "less"
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    XML = "xml"
    MARKDOWN = "markdown"
    DOCKERFILE = "dockerfile"
    TERRAFORM = "terraform"
    PROTOBUF = "protobuf"
    GRAPHQL = "graphql"
    UNKNOWN = "unknown"


class ChangeMagnitude(StrEnum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    VERY_LARGE = "very_large"


class ClassificationMatch(StrictClassificationModel):
    rule_id: str = Field(description="Stable rule identifier.")
    match_type: str = Field(description="Kind of rule evidence.")
    value: str = Field(description="Matched value.")
    description: str = Field(description="Concise explanation of the match.")


class FileContext(StrictClassificationModel):
    framework: str | None = Field(default=None, description="Observable framework or convention.")
    component_role: str | None = Field(default=None, description="Observable component or file role.")
    route_context: list[str] = Field(default_factory=list, description="Observable route context labels.")
    access_context: list[str] = Field(default_factory=list, description="Observable access context labels.")
    domains: list[str] = Field(default_factory=list, description="Bounded path-derived product domains.")
    areas: list[str] = Field(default_factory=list, description="Human-readable contextual areas.")
    is_user_facing: bool = Field(default=False, description="Whether path convention suggests user-facing behavior.")
    is_dynamic_route: bool = Field(default=False, description="Whether a route segment is dynamic.")
    is_test: bool = Field(default=False, description="Whether this is test-related.")
    is_generated: bool = Field(default=False, description="Whether this is generated or vendored.")
    is_configuration: bool = Field(default=False, description="Whether this is configuration-related.")
    is_documentation: bool = Field(default=False, description="Whether this is documentation-related.")
    is_database_change: bool = Field(default=False, description="Whether this is database-related.")
    classification_confidence: str = Field(default="medium", description="Path-context confidence: high, medium, or low.")
    evidence: list[ClassificationMatch] = Field(default_factory=list, description="Evidence behind the file context.")
    warnings: list[str] = Field(default_factory=list, description="Safe context warnings.")


class FileClassification(StrictClassificationModel):
    primary_kind: FileKind = Field(description="Resolved primary file kind.")
    areas: list[FileArea] = Field(description="Functional areas matched by the file.")
    language: FileLanguage = Field(description="Detected language or technology.")
    context: FileContext = Field(default_factory=FileContext, description="Observable path-derived file context.")
    matches: list[ClassificationMatch] = Field(description="Evidence behind the classification.")
    warnings: list[str] = Field(description="Safe classification warnings.")


class ClassificationCount(StrictClassificationModel):
    name: str = Field(description="Classification enum value.")
    count: int = Field(description="Number of files with this value.")


class FileClassificationSummary(StrictClassificationModel):
    total_files: int = Field(description="Total changed files.")
    classified_files: int = Field(description="Files with a non-unknown primary kind.")
    unknown_files: int = Field(description="Files with unknown primary kind.")
    counts_by_kind: list[ClassificationCount] = Field(description="Counts by primary file kind.")
    counts_by_area: list[ClassificationCount] = Field(description="Counts by functional area.")
    counts_by_language: list[ClassificationCount] = Field(description="Counts by language.")
    renamed_files: int = Field(description="Files marked renamed or carrying a previous filename.")
    files_with_previous_classification: int = Field(description="Files with previous path classification.")
    files_without_patch: int = Field(description="Files without patch data.")
    warnings: list[str] = Field(description="Classification summary warnings.")
