from dataclasses import dataclass
from types import MappingProxyType

from app.domain.file_classification import FileArea, FileKind

FILE_PRIORITY_RULES_VERSION = "v1"
MAX_FILE_PRIORITY_SCORE = 100

FACTOR_GROUP_ORDER: tuple[str, ...] = (
    "signal_impact",
    "sensitive_area",
    "change_size",
    "visibility",
    "rename_transition",
)

FACTOR_GROUP_CAPS = MappingProxyType({
    "signal_impact": 50,
    "sensitive_area": 25,
    "change_size": 15,
    "visibility": 5,
    "rename_transition": 5,
})


@dataclass(frozen=True)
class SignalPriorityWeight:
    rule_id: str
    points: int
    description: str


SIGNAL_PRIORITY_WEIGHTS: tuple[SignalPriorityWeight, ...] = (
    SignalPriorityWeight("security.credential_like_literal_added", 25, "Credential-like literal pattern affected this file."),
    SignalPriorityWeight("security.security_control_disabled_hint", 22, "Security-control disabling pattern affected this file."),
    SignalPriorityWeight("database.destructive_migration_hint", 22, "Destructive migration pattern affected this file."),
    SignalPriorityWeight("authentication.paths_changed", 12, "Authentication-related path classification affected this file."),
    SignalPriorityWeight("authorization.paths_changed", 12, "Authorization-related path classification affected this file."),
    SignalPriorityWeight("database.migration_changed", 12, "Database migration classification affected this file."),
    SignalPriorityWeight("testing.sensitive_change_without_test_files", 10, "Sensitive-area change without changed test files affected this file."),
    SignalPriorityWeight("testing.test_files_deleted", 10, "Deleted test file signal affected this file."),
    SignalPriorityWeight("testing.test_skip_added", 8, "Test skip pattern affected this file."),
    SignalPriorityWeight("api.surface_changed", 6, "API surface classification affected this file."),
    SignalPriorityWeight("infrastructure.configuration_changed", 6, "Infrastructure classification affected this file."),
    SignalPriorityWeight("ci.configuration_changed", 6, "CI configuration classification affected this file."),
    SignalPriorityWeight("configuration.runtime_configuration_changed", 5, "Runtime configuration classification affected this file."),
    SignalPriorityWeight("database.migration_without_patch_visibility", 5, "Migration patch visibility affected this file."),
    SignalPriorityWeight("rename.file_moved_into_sensitive_area", 5, "Rename transition into a sensitive area affected this file."),
    SignalPriorityWeight("rename.file_moved_out_of_test_area", 4, "Rename transition out of test classification affected this file."),
    SignalPriorityWeight("code_quality.empty_exception_handler_added", 4, "Empty exception handler pattern affected this file."),
    SignalPriorityWeight("code_quality.lint_or_type_suppression_added", 3, "Lint or type suppression pattern affected this file."),
    SignalPriorityWeight("code_quality.debug_statement_added", 2, "Debug statement pattern affected this file."),
    SignalPriorityWeight("generated_content.large_generated_change", 2, "Large generated-content signal affected this file."),
    SignalPriorityWeight("completeness.opaque_files_changed", 2, "Opaque or patchless-file signal affected this file."),
    SignalPriorityWeight("code_quality.todo_or_fixme_added", 1, "TODO or FIXME marker affected this file."),
    SignalPriorityWeight("generated_content.generated_files_changed", 1, "Generated-file classification affected this file."),
    SignalPriorityWeight("rename.file_moved_into_generated_area", 1, "Rename transition into generated classification affected this file."),
)

SIGNAL_PRIORITY_WEIGHT_BY_RULE_ID = MappingProxyType({
    weight.rule_id: weight for weight in SIGNAL_PRIORITY_WEIGHTS
})

SENSITIVE_AREA_WEIGHTS = MappingProxyType({
    FileArea.SECURITY: 15,
    FileArea.AUTHENTICATION: 12,
    FileArea.AUTHORIZATION: 12,
    FileArea.DATABASE: 8,
    FileArea.INFRASTRUCTURE: 7,
    FileArea.CI_CD: 7,
    FileArea.API: 5,
    FileArea.CONFIGURATION: 5,
})

SENSITIVE_KIND_WEIGHTS = MappingProxyType({
    FileKind.DATABASE_MIGRATION: 12,
})

RENAME_SENSITIVE_AREAS = frozenset({
    FileArea.SECURITY,
    FileArea.AUTHENTICATION,
    FileArea.AUTHORIZATION,
    FileArea.DATABASE,
    FileArea.CI_CD,
    FileArea.INFRASTRUCTURE,
})
