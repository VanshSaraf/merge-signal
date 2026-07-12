from dataclasses import dataclass
from types import MappingProxyType

from app.domain.scoring import RiskGroup

SCORING_RULES_VERSION = "v1"
MAX_SCORE = 100

RISK_GROUP_ORDER: tuple[RiskGroup, ...] = (
    RiskGroup.CHANGE_SCOPE,
    RiskGroup.SENSITIVE_SYSTEMS,
    RiskGroup.TESTING,
    RiskGroup.CI,
    RiskGroup.OPERATIONAL_CHANGE,
    RiskGroup.CODE_QUALITY,
)

RISK_GROUP_CAPS = MappingProxyType({
    RiskGroup.CHANGE_SCOPE: 20,
    RiskGroup.SENSITIVE_SYSTEMS: 25,
    RiskGroup.TESTING: 15,
    RiskGroup.CI: 20,
    RiskGroup.OPERATIONAL_CHANGE: 15,
    RiskGroup.CODE_QUALITY: 5,
})


@dataclass(frozen=True)
class RiskRuleWeight:
    rule_id: str
    group: RiskGroup
    points: int


RISK_RULE_WEIGHTS: tuple[RiskRuleWeight, ...] = (
    RiskRuleWeight("scope.large_file_count", RiskGroup.CHANGE_SCOPE, 8),
    RiskRuleWeight("scope.very_large_file_count", RiskGroup.CHANGE_SCOPE, 15),
    RiskRuleWeight("scope.large_line_churn", RiskGroup.CHANGE_SCOPE, 8),
    RiskRuleWeight("scope.very_large_line_churn", RiskGroup.CHANGE_SCOPE, 15),
    RiskRuleWeight("scope.large_individual_file_change", RiskGroup.CHANGE_SCOPE, 6),
    RiskRuleWeight("scope.broad_functional_change", RiskGroup.CHANGE_SCOPE, 8),
    RiskRuleWeight("metadata.large_commit_count", RiskGroup.CHANGE_SCOPE, 3),
    RiskRuleWeight("authentication.paths_changed", RiskGroup.SENSITIVE_SYSTEMS, 10),
    RiskRuleWeight("authorization.paths_changed", RiskGroup.SENSITIVE_SYSTEMS, 10),
    RiskRuleWeight("database.migration_changed", RiskGroup.SENSITIVE_SYSTEMS, 10),
    RiskRuleWeight("database.destructive_migration_hint", RiskGroup.SENSITIVE_SYSTEMS, 15),
    RiskRuleWeight("api.surface_changed", RiskGroup.SENSITIVE_SYSTEMS, 6),
    RiskRuleWeight("security.credential_like_literal_added", RiskGroup.SENSITIVE_SYSTEMS, 18),
    RiskRuleWeight("security.security_control_disabled_hint", RiskGroup.SENSITIVE_SYSTEMS, 15),
    RiskRuleWeight("rename.file_moved_into_sensitive_area", RiskGroup.SENSITIVE_SYSTEMS, 7),
    RiskRuleWeight("testing.production_change_without_test_files", RiskGroup.TESTING, 7),
    RiskRuleWeight("testing.sensitive_change_without_test_files", RiskGroup.TESTING, 12),
    RiskRuleWeight("testing.test_files_deleted", RiskGroup.TESTING, 12),
    RiskRuleWeight("testing.test_skip_added", RiskGroup.TESTING, 10),
    RiskRuleWeight("ci.failing", RiskGroup.CI, 18),
    RiskRuleWeight("ci.pending", RiskGroup.CI, 6),
    RiskRuleWeight("ci.missing", RiskGroup.CI, 8),
    RiskRuleWeight("ci.unavailable", RiskGroup.CI, 6),
    RiskRuleWeight("ci.partial_visibility", RiskGroup.CI, 4),
    RiskRuleWeight("ci.unknown_outcome", RiskGroup.CI, 5),
    RiskRuleWeight("dependencies.manifest_changed", RiskGroup.OPERATIONAL_CHANGE, 4),
    RiskRuleWeight("dependencies.lockfile_changed", RiskGroup.OPERATIONAL_CHANGE, 1),
    RiskRuleWeight("dependencies.manifest_without_lockfile", RiskGroup.OPERATIONAL_CHANGE, 7),
    RiskRuleWeight("dependencies.lockfile_only_change", RiskGroup.OPERATIONAL_CHANGE, 0),
    RiskRuleWeight("infrastructure.configuration_changed", RiskGroup.OPERATIONAL_CHANGE, 7),
    RiskRuleWeight("ci.configuration_changed", RiskGroup.OPERATIONAL_CHANGE, 6),
    RiskRuleWeight("configuration.runtime_configuration_changed", RiskGroup.OPERATIONAL_CHANGE, 5),
    RiskRuleWeight("database.migration_without_patch_visibility", RiskGroup.OPERATIONAL_CHANGE, 6),
    RiskRuleWeight("rename.file_moved_out_of_test_area", RiskGroup.OPERATIONAL_CHANGE, 6),
    RiskRuleWeight("code_quality.debug_statement_added", RiskGroup.CODE_QUALITY, 2),
    RiskRuleWeight("code_quality.todo_or_fixme_added", RiskGroup.CODE_QUALITY, 1),
    RiskRuleWeight("code_quality.lint_or_type_suppression_added", RiskGroup.CODE_QUALITY, 3),
    RiskRuleWeight("code_quality.empty_exception_handler_added", RiskGroup.CODE_QUALITY, 4),
    RiskRuleWeight("generated_content.large_generated_change", RiskGroup.CODE_QUALITY, 2),
    RiskRuleWeight("completeness.opaque_files_changed", RiskGroup.CODE_QUALITY, 2),
    RiskRuleWeight("rename.file_moved_into_generated_area", RiskGroup.CODE_QUALITY, 1),
    RiskRuleWeight("metadata.draft_pull_request", RiskGroup.CHANGE_SCOPE, 0),
    RiskRuleWeight("metadata.missing_description", RiskGroup.CHANGE_SCOPE, 0),
    RiskRuleWeight("testing.test_files_changed", RiskGroup.TESTING, 0),
    RiskRuleWeight("testing.only_test_or_documentation_changes", RiskGroup.TESTING, 0),
    RiskRuleWeight("generated_content.generated_files_changed", RiskGroup.CODE_QUALITY, 0),
    RiskRuleWeight("completeness.file_collection_incomplete", RiskGroup.CODE_QUALITY, 0),
    RiskRuleWeight("completeness.commit_collection_incomplete", RiskGroup.CODE_QUALITY, 0),
    RiskRuleWeight("completeness.patch_coverage_incomplete", RiskGroup.CODE_QUALITY, 0),
)

RISK_RULE_BY_ID = MappingProxyType({rule.rule_id: rule for rule in RISK_RULE_WEIGHTS})
