from dataclasses import dataclass

from app.domain.review_signal import SignalCategory, SignalScope, SignalSeverity


RULES_VERSION = "v1"

LARGE_COMMIT_COUNT = 20
LARGE_FILE_COUNT = 25
VERY_LARGE_FILE_COUNT = 75
LARGE_TOTAL_CHURN = 1000
VERY_LARGE_TOTAL_CHURN = 3000
LARGE_INDIVIDUAL_FILE_CHANGE = 500
BROAD_FUNCTIONAL_AREA_COUNT = 4
LARGE_GENERATED_FILE_COUNT = 25
LARGE_GENERATED_CHURN = 500
MAX_EVIDENCE_ITEMS_PER_SIGNAL = 25

SIGNIFICANT_AREA_EXCLUSIONS = frozenset({"documentation", "generated"})
SENSITIVE_RENAME_AREAS = frozenset({"authentication", "authorization", "security", "database", "ci_cd", "infrastructure"})


@dataclass(frozen=True)
class SignalRule:
    rule_id: str
    title: str
    description: str
    category: SignalCategory
    severity: SignalSeverity
    scope: SignalScope
    limitations: tuple[str, ...]
    tags: tuple[str, ...]


RULES: tuple[SignalRule, ...] = (
    SignalRule("metadata.missing_description", "Pull request description is missing", "The pull-request body is empty after trimming.", SignalCategory.METADATA, SignalSeverity.LOW, SignalScope.PULL_REQUEST, ("A missing description does not imply the implementation is incorrect.",), ("metadata", "description")),
    SignalRule("metadata.draft_pull_request", "Pull request is marked as draft", "GitHub reports the pull request as a draft.", SignalCategory.METADATA, SignalSeverity.INFO, SignalScope.PULL_REQUEST, ("Draft status is contextual and does not describe code correctness.",), ("metadata", "draft")),
    SignalRule("metadata.large_commit_count", "Pull request contains many commits", "The pull request contains at least the configured commit-count threshold.", SignalCategory.METADATA, SignalSeverity.LOW, SignalScope.PULL_REQUEST, ("Commit count is a review-navigation signal, not a correctness claim.",), ("metadata", "commits")),
    SignalRule("metadata.merge_conflict_observed", "GitHub reports a merge conflict condition", "GitHub reports mergeability data consistent with a conflict condition.", SignalCategory.METADATA, SignalSeverity.HIGH, SignalScope.PULL_REQUEST, ("GitHub mergeability may be temporarily unavailable or recomputed.",), ("metadata", "mergeability")),
    SignalRule("scope.large_file_count", "Pull request changes many files", "The changed-file count reaches the configured large-file threshold.", SignalCategory.CHANGE_SCOPE, SignalSeverity.MEDIUM, SignalScope.PULL_REQUEST, ("File count alone does not describe implementation risk.",), ("scope", "file_count")),
    SignalRule("scope.very_large_file_count", "Pull request changes a very large number of files", "The changed-file count reaches the configured very-large-file threshold.", SignalCategory.CHANGE_SCOPE, SignalSeverity.HIGH, SignalScope.PULL_REQUEST, ("File count alone does not describe implementation risk.",), ("scope", "file_count")),
    SignalRule("scope.large_line_churn", "Pull request has large line churn", "Total additions plus deletions reaches the configured large-churn threshold.", SignalCategory.CHANGE_SCOPE, SignalSeverity.MEDIUM, SignalScope.PULL_REQUEST, ("Line churn does not indicate whether the change is correct.",), ("scope", "churn")),
    SignalRule("scope.very_large_line_churn", "Pull request has very large line churn", "Total additions plus deletions reaches the configured very-large-churn threshold.", SignalCategory.CHANGE_SCOPE, SignalSeverity.HIGH, SignalScope.PULL_REQUEST, ("Line churn does not indicate whether the change is correct.",), ("scope", "churn")),
    SignalRule("scope.large_individual_file_change", "Large individual file change", "One or more changed files reach the configured per-file change threshold.", SignalCategory.CHANGE_SCOPE, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("A large file change can still be mechanical or low complexity.",), ("scope", "file_churn")),
    SignalRule("scope.broad_functional_change", "Pull request spans several functional areas", "Changed files collectively span at least the configured significant-area threshold.", SignalCategory.CHANGE_SCOPE, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("Functional areas are path-based labels and do not prove behavioral coupling.",), ("scope", "areas")),
    SignalRule("authentication.paths_changed", "Authentication-related paths changed", "One or more changed files are classified in the authentication area.", SignalCategory.AUTHENTICATION, SignalSeverity.HIGH, SignalScope.FILE_SET, ("Path classification does not prove authentication behavior changed.",), ("classification", "authentication")),
    SignalRule("authorization.paths_changed", "Authorization-related paths changed", "One or more changed files are classified in the authorization area.", SignalCategory.AUTHORIZATION, SignalSeverity.HIGH, SignalScope.FILE_SET, ("Path classification does not prove authorization behavior changed.",), ("classification", "authorization")),
    SignalRule("database.migration_changed", "Database migration files changed", "One or more changed files are classified as database migrations.", SignalCategory.DATABASE, SignalSeverity.HIGH, SignalScope.FILE_SET, ("Migration classification is path-based and does not validate migration behavior.",), ("classification", "database")),
    SignalRule("api.surface_changed", "API surface paths changed", "One or more production-relevant changed files are classified in the API area.", SignalCategory.API, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("Path classification does not prove external API behavior changed.",), ("classification", "api")),
    SignalRule("infrastructure.configuration_changed", "Infrastructure configuration changed", "One or more changed files are classified as infrastructure or infrastructure-area files.", SignalCategory.INFRASTRUCTURE, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("Infrastructure classification is path-based and does not validate deployment impact.",), ("classification", "infrastructure")),
    SignalRule("ci.configuration_changed", "CI configuration changed", "One or more changed files are classified as CI configuration or CI/CD-area files.", SignalCategory.CI, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("This does not infer required checks or CI policy.",), ("classification", "ci")),
    SignalRule("configuration.runtime_configuration_changed", "Runtime configuration paths changed", "One or more changed files match conservative runtime-configuration patterns.", SignalCategory.CONFIGURATION, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("Configuration path matching does not prove runtime behavior changed.",), ("classification", "configuration")),
    SignalRule("testing.production_change_without_test_files", "No test files were changed in this pull request", "Production-relevant files changed and no current changed file is classified as a test.", SignalCategory.TESTING, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("This does not prove test coverage is absent.",), ("testing", "coverage_evidence")),
    SignalRule("testing.sensitive_change_without_test_files", "Sensitive-area change without changed test files", "Sensitive production-relevant files changed and no current changed file is classified as a test.", SignalCategory.TESTING, SignalSeverity.HIGH, SignalScope.FILE_SET, ("This does not prove test coverage is absent.",), ("testing", "sensitive")),
    SignalRule("testing.test_files_deleted", "Test files were removed", "One or more changed files classified as tests were removed.", SignalCategory.TESTING, SignalSeverity.HIGH, SignalScope.FILE_SET, ("Removing a test file may be intentional and is not a correctness claim.",), ("testing", "removed")),
    SignalRule("testing.test_files_changed", "Test files changed", "One or more changed files are classified as tests.", SignalCategory.TESTING, SignalSeverity.INFO, SignalScope.FILE_SET, ("This is contextual and does not prove coverage quality.",), ("testing", "context")),
    SignalRule("testing.only_test_or_documentation_changes", "Only test or documentation files changed", "All changed files are classified as tests or documentation.", SignalCategory.TESTING, SignalSeverity.INFO, SignalScope.FILE_SET, ("This does not prove the pull request is safe or low risk.",), ("testing", "documentation")),
    SignalRule("ci.failing", "CI reports a failing state", "The normalized CI state is failing for the current head SHA.", SignalCategory.CI, SignalSeverity.HIGH, SignalScope.CI_SURFACE, ("CI state is based only on observed check runs and commit statuses.",), ("ci", "state")),
    SignalRule("ci.pending", "CI reports a pending state", "The normalized CI state is pending for the current head SHA.", SignalCategory.CI, SignalSeverity.MEDIUM, SignalScope.CI_SURFACE, ("Pending CI may change after the snapshot is collected.",), ("ci", "state")),
    SignalRule("ci.missing", "No CI records were observed", "No check runs or commit-status contexts were observed for the current head SHA.", SignalCategory.CI, SignalSeverity.MEDIUM, SignalScope.CI_SURFACE, ("This does not state that the repository has no CI configuration.",), ("ci", "state")),
    SignalRule("ci.unavailable", "CI data was unavailable", "MergeSignal could not observe either CI surface for the current head SHA.", SignalCategory.CI, SignalSeverity.MEDIUM, SignalScope.CI_SURFACE, ("Unavailable CI visibility does not imply CI is absent.",), ("ci", "visibility")),
    SignalRule("ci.partial_visibility", "CI visibility was partial", "MergeSignal observed only part of the CI surface for the current head SHA.", SignalCategory.CI, SignalSeverity.MEDIUM, SignalScope.CI_SURFACE, ("Partial CI visibility can omit relevant check or status records.",), ("ci", "visibility")),
    SignalRule("ci.unknown_outcome", "CI outcome could not be classified", "Observed CI records contain states or conclusions that are not classified by the current CI model.", SignalCategory.CI, SignalSeverity.MEDIUM, SignalScope.CI_SURFACE, ("Unknown CI state is not interpreted as passing or failing.",), ("ci", "state")),
    SignalRule("dependencies.manifest_changed", "Dependency manifest changed", "One or more dependency manifest files changed.", SignalCategory.DEPENDENCIES, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("Dependency manifest changes do not prove dependency behavior changed at runtime.",), ("dependencies", "manifest")),
    SignalRule("dependencies.lockfile_changed", "Dependency lockfile changed", "One or more dependency lockfiles changed.", SignalCategory.DEPENDENCIES, SignalSeverity.LOW, SignalScope.FILE_SET, ("Lockfile changes may be expected companion metadata.",), ("dependencies", "lockfile")),
    SignalRule("dependencies.manifest_without_lockfile", "Dependency manifest changed without companion lockfile", "A manifest with a known lockfile convention changed without a companion lockfile change.", SignalCategory.DEPENDENCIES, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("This rule uses conservative ecosystem conventions and does not prove a lockfile is required.",), ("dependencies", "lockfile")),
    SignalRule("dependencies.lockfile_only_change", "Only dependency lockfiles changed", "Dependency lockfiles changed without dependency manifests or other production-relevant files.", SignalCategory.DEPENDENCIES, SignalSeverity.INFO, SignalScope.FILE_SET, ("Lockfile-only changes may be intentional and are not treated as incorrect.",), ("dependencies", "lockfile")),
    SignalRule("database.destructive_migration_hint", "Destructive migration pattern detected", "Added patch content in migration files contains a controlled destructive-SQL pattern.", SignalCategory.DATABASE, SignalSeverity.HIGH, SignalScope.FILE_SET, ("This heuristic does not determine whether the migration is safe or unsafe.",), ("patch", "database")),
    SignalRule("database.migration_without_patch_visibility", "Patch-level migration inspection was unavailable", "One or more database migration files changed without GitHub patch visibility.", SignalCategory.DATABASE, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("This signal is about visibility, not migration correctness.",), ("patch", "database", "visibility")),
    SignalRule("code_quality.debug_statement_added", "Debug statement pattern added", "Added patch content contains a controlled debug-statement pattern.", SignalCategory.CODE_QUALITY, SignalSeverity.LOW, SignalScope.FILE_SET, ("This heuristic is line-based and does not parse complete source files.",), ("patch", "debug")),
    SignalRule("code_quality.todo_or_fixme_added", "TODO or FIXME comment added", "Added patch content contains a likely TODO or FIXME comment marker.", SignalCategory.CODE_QUALITY, SignalSeverity.LOW, SignalScope.FILE_SET, ("This is a review-navigation hint, not a correctness claim.",), ("patch", "todo")),
    SignalRule("testing.test_skip_added", "Test skip pattern added", "Added patch content contains a controlled test-skip or expected-failure pattern.", SignalCategory.TESTING, SignalSeverity.HIGH, SignalScope.FILE_SET, ("This does not determine whether the skip is justified.",), ("patch", "testing")),
    SignalRule("code_quality.lint_or_type_suppression_added", "Lint or type suppression added", "Added patch content contains a controlled lint or type suppression pattern.", SignalCategory.CODE_QUALITY, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("This does not determine whether the suppression is necessary.",), ("patch", "suppression")),
    SignalRule("code_quality.empty_exception_handler_added", "Empty exception handler pattern added", "Added Python patch lines contain an exception handler followed by pass in the same hunk.", SignalCategory.CODE_QUALITY, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("This heuristic does not parse Python ASTs or infer intent.",), ("patch", "exception")),
    SignalRule("security.credential_like_literal_added", "Credential-like literal pattern added", "An added patch line contains a literal assignment to a credential-related identifier.", SignalCategory.SECURITY, SignalSeverity.HIGH, SignalScope.FILE_SET, ("This heuristic does not verify whether the value is valid, active, or sensitive.",), ("patch", "security")),
    SignalRule("security.security_control_disabled_hint", "Security-control disable pattern added", "Added patch content contains a controlled pattern for disabling a security-related control.", SignalCategory.SECURITY, SignalSeverity.HIGH, SignalScope.FILE_SET, ("This heuristic does not determine whether the setting is reachable or intentional.",), ("patch", "security")),
    SignalRule("generated_content.generated_files_changed", "Generated files changed", "One or more changed files are classified as generated.", SignalCategory.GENERATED_CONTENT, SignalSeverity.INFO, SignalScope.FILE_SET, ("Generated classification is path-based and does not prove generation provenance.",), ("classification", "generated")),
    SignalRule("generated_content.large_generated_change", "Large generated-content change", "Generated files reach the configured generated-file count or churn threshold.", SignalCategory.GENERATED_CONTENT, SignalSeverity.LOW, SignalScope.FILE_SET, ("Large generated changes may be expected outputs.",), ("classification", "generated")),
    SignalRule("completeness.opaque_files_changed", "Opaque or patchless files changed", "Binary files or files without patch visibility changed.", SignalCategory.COMPLETENESS, SignalSeverity.MEDIUM, SignalScope.SNAPSHOT, ("Opaque changes limit patch-level review visibility.",), ("completeness", "visibility")),
    SignalRule("rename.file_moved_into_sensitive_area", "File moved into sensitive area", "A renamed file moved from a non-sensitive classification into a sensitive functional area.", SignalCategory.RENAME, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("Rename classification does not infer intent.",), ("rename", "classification")),
    SignalRule("rename.file_moved_out_of_test_area", "File moved out of test area", "A renamed file moved from test classification to a non-test classification.", SignalCategory.RENAME, SignalSeverity.MEDIUM, SignalScope.FILE_SET, ("Rename classification does not infer intent.",), ("rename", "testing")),
    SignalRule("rename.file_moved_into_generated_area", "File moved into generated area", "A renamed file moved from non-generated classification into generated classification.", SignalCategory.RENAME, SignalSeverity.INFO, SignalScope.FILE_SET, ("Rename classification does not infer intent.",), ("rename", "generated")),
    SignalRule("completeness.patch_coverage_incomplete", "Patch coverage is incomplete", "Snapshot completeness reports missing GitHub patch data.", SignalCategory.COMPLETENESS, SignalSeverity.MEDIUM, SignalScope.SNAPSHOT, ("Missing patch data can occur for binary or very large files.",), ("completeness", "patch")),
    SignalRule("completeness.file_collection_incomplete", "Changed-file collection is incomplete", "GitHub reported more changed files than MergeSignal retrieved.", SignalCategory.COMPLETENESS, SignalSeverity.HIGH, SignalScope.SNAPSHOT, ("Signal detection only covers retrieved files.",), ("completeness", "files")),
    SignalRule("completeness.commit_collection_incomplete", "Commit collection is incomplete", "GitHub reported a different commit count than MergeSignal retrieved.", SignalCategory.COMPLETENESS, SignalSeverity.MEDIUM, SignalScope.SNAPSHOT, ("Commit-derived signals only cover retrieved commit metadata.",), ("completeness", "commits")),
)

RULE_BY_ID = {rule.rule_id: rule for rule in RULES}

SEVERITY_ORDER = {
    SignalSeverity.HIGH: 0,
    SignalSeverity.MEDIUM: 1,
    SignalSeverity.LOW: 2,
    SignalSeverity.INFO: 3,
}

CATEGORY_ORDER = {category: index for index, category in enumerate(SignalCategory)}
