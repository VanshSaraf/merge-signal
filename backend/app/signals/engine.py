from dataclasses import dataclass, field
import re

from app.domain.file_classification import FileArea, FileKind, FileLanguage
from app.domain.pull_request import ChangedFile, CiState, CiVisibility, PullRequestSnapshot
from app.domain.review_signal import (
    EvidenceKind,
    ReviewSignal,
    SignalDetectionResult,
    SignalEvidence,
)
from app.signals.patch_scanner import PatchLineKind, added_lines_by_hunk, parse_patch
from app.signals.rules import (
    BROAD_FUNCTIONAL_AREA_COUNT,
    CATEGORY_ORDER,
    LARGE_COMMIT_COUNT,
    LARGE_FILE_COUNT,
    LARGE_GENERATED_CHURN,
    LARGE_GENERATED_FILE_COUNT,
    LARGE_INDIVIDUAL_FILE_CHANGE,
    LARGE_TOTAL_CHURN,
    MAX_EVIDENCE_ITEMS_PER_SIGNAL,
    RULE_BY_ID,
    SENSITIVE_RENAME_AREAS,
    SEVERITY_ORDER,
    SIGNIFICANT_AREA_EXCLUSIONS,
    VERY_LARGE_FILE_COUNT,
    VERY_LARGE_TOTAL_CHURN,
    SignalRule,
)
from app.signals.summary import build_signal_summary


DEPENDENCY_LOCKFILES_BY_MANIFEST = {
    "package.json": {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "npm-shrinkwrap.json"},
    "pipfile": {"pipfile.lock"},
}
RUNTIME_CONFIG_FILENAMES = {
    ".env",
    ".env.local",
    "application.yml",
    "application.yaml",
    "application.properties",
    "settings.py",
    "config.py",
}
PRODUCTION_RELEVANT_KINDS = {
    FileKind.SOURCE,
    FileKind.DATABASE_MIGRATION,
    FileKind.DEPENDENCY_MANIFEST,
    FileKind.CI_CONFIGURATION,
    FileKind.INFRASTRUCTURE,
    FileKind.CONFIGURATION,
}
API_EXCLUDED_KINDS = {FileKind.DOCUMENTATION, FileKind.GENERATED, FileKind.TEST}
PATCH_SCAN_EXCLUDED_KINDS = {FileKind.DOCUMENTATION, FileKind.GENERATED, FileKind.ASSET, FileKind.BINARY}
SECRET_PLACEHOLDERS = {"changeme", "change_me", "example", "dummy", "test", "placeholder", "your_key_here", "redacted", "null", "none"}

DEBUG_PATTERNS = (
    ("console_log", re.compile(r"^\s*console\.(log|debug)\s*\(")),
    ("debugger", re.compile(r"^\s*debugger\s*;?\s*$")),
    ("python_print", re.compile(r"^\s*print\s*\(")),
    ("python_pprint", re.compile(r"^\s*pprint\s*\(")),
    ("python_breakpoint", re.compile(r"^\s*breakpoint\s*\(")),
    ("python_pdb", re.compile(r"pdb\.set_trace\s*\(")),
    ("go_fmt_println", re.compile(r"^\s*fmt\.Println\s*\(")),
    ("java_system_out", re.compile(r"System\.out\.println\s*\(")),
    ("php_var_dump", re.compile(r"\bvar_dump\s*\(")),
    ("php_dd", re.compile(r"\bdd\s*\(")),
)
TODO_PATTERN = re.compile(r"^\s*(#|//|/\*|\*|<!--).*\b(TODO|FIXME)\b", re.IGNORECASE)
TEST_SKIP_PATTERNS = (
    ("pytest_skip", re.compile(r"pytest\.mark\.(skip|xfail)")),
    ("unittest_skip", re.compile(r"@unittest\.skip")),
    ("js_skip", re.compile(r"\b(test|it|describe)\.skip\s*\(")),
    ("js_xskip", re.compile(r"\bx(it|describe)\s*\(")),
    ("java_disabled", re.compile(r"@Disabled\b")),
    ("go_skip", re.compile(r"\bt\.Skip(Now)?\s*\(")),
)
SUPPRESSION_PATTERNS = (
    ("eslint_disable", re.compile(r"eslint-disable")),
    ("noqa", re.compile(r"#\s*noqa\b")),
    ("type_ignore", re.compile(r"type:\s*ignore")),
    ("suppress_warnings", re.compile(r"@SuppressWarnings")),
    ("nolint", re.compile(r"nolint")),
    ("prettier_ignore", re.compile(r"prettier-ignore")),
    ("ts_ignore", re.compile(r"ts-(ignore|expect-error)")),
)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"""(?ix)
    (?P<name>password|passwd|secret|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|private[_-]?key|client[_-]?secret)
    ["']?\s*[:=]\s*
    (?P<value>["'][^"']+["']|[A-Za-z0-9_./+=-]{4,})
    """
)
SAFE_REFERENCE_PATTERN = re.compile(r"(process\.env\.|os\.getenv\s*\(|getenv\s*\(|config\s*\(|secrets\.|\$\{\{\s*secrets\.)", re.IGNORECASE)
SECURITY_DISABLE_PATTERNS = (
    ("verify_false", re.compile(r"\b(verify|ssl_verify)\s*=\s*False\b")),
    ("reject_unauthorized_false", re.compile(r"\brejectUnauthorized\s*:\s*false\b")),
    ("node_tls_disabled", re.compile(r"\bNODE_TLS_REJECT_UNAUTHORIZED\s*=\s*0\b")),
    ("curl_ssl_verify_disabled", re.compile(r"\bCURLOPT_SSL_VERIFYPEER\b.*\b(false|0)\b", re.IGNORECASE)),
    ("go_insecure_skip_verify", re.compile(r"\bInsecureSkipVerify\s*:\s*true\b")),
)
DESTRUCTIVE_SQL_PATTERNS = (
    ("drop_table", re.compile(r"\bdrop\s+table\b", re.IGNORECASE)),
    ("drop_column", re.compile(r"\bdrop\s+column\b", re.IGNORECASE)),
    ("truncate_table", re.compile(r"\btruncate\s+table\b", re.IGNORECASE)),
    ("alter_table_drop", re.compile(r"\balter\s+table\b.*\bdrop\b", re.IGNORECASE)),
    ("drop_index", re.compile(r"\bdrop\s+index\b", re.IGNORECASE)),
    ("drop_constraint", re.compile(r"\bdrop\s+constraint\b", re.IGNORECASE)),
)


@dataclass
class SignalAccumulator:
    rule: SignalRule
    affected_files: set[str] = field(default_factory=set)
    evidence: set[tuple[str, str, str, str, str]] = field(default_factory=set)
    extra_limitations: set[str] = field(default_factory=set)


def analyze_snapshot_signals(snapshot: PullRequestSnapshot) -> SignalDetectionResult:
    accumulators: dict[str, SignalAccumulator] = {}
    warnings: list[str] = []

    def emit(
        rule_id: str,
        affected_files: list[str] | None = None,
        evidence: list[SignalEvidence] | None = None,
        extra_limitations: list[str] | None = None,
    ) -> None:
        accumulator = accumulators.setdefault(rule_id, SignalAccumulator(rule=RULE_BY_ID[rule_id]))
        accumulator.affected_files.update(affected_files or [])
        for item in evidence or []:
            accumulator.evidence.add(_evidence_key(item))
        accumulator.extra_limitations.update(extra_limitations or [])

    _detect_metadata(snapshot, emit)
    _detect_scope(snapshot, emit)
    sensitive_files = _detect_classification(snapshot.files, emit)
    has_tests = any(file.classification.primary_kind == FileKind.TEST for file in snapshot.files)
    _detect_testing(snapshot.files, has_tests, sensitive_files, emit)
    _detect_ci(snapshot, emit)
    _detect_dependencies(snapshot.files, emit)
    migration_patchless_files = _detect_patch_signals(snapshot.files, emit, warnings)
    _detect_generated_and_opaque(snapshot.files, migration_patchless_files, emit)
    _detect_renames(snapshot.files, emit)
    _detect_completeness(snapshot, migration_patchless_files, emit)

    signals = _build_signals(accumulators)
    return SignalDetectionResult(signals=signals, summary=build_signal_summary(signals, warnings))


def detect_review_signals(snapshot: PullRequestSnapshot) -> list[ReviewSignal]:
    return analyze_snapshot_signals(snapshot).signals


def _detect_metadata(snapshot: PullRequestSnapshot, emit) -> None:
    metadata = snapshot.metadata
    if metadata.body is None or not metadata.body.strip():
        emit("metadata.missing_description", evidence=[_e(EvidenceKind.METADATA, "Pull-request body is empty.", observed="missing_description")])
    if metadata.draft:
        emit("metadata.draft_pull_request", evidence=[_e(EvidenceKind.METADATA, "Pull request is marked as draft.", observed="draft")])
    if metadata.commit_count >= LARGE_COMMIT_COUNT:
        emit("metadata.large_commit_count", evidence=[_e(EvidenceKind.COMMIT_COUNT, "Commit count reached the configured threshold.", observed=str(metadata.commit_count), expected=f">= {LARGE_COMMIT_COUNT}")])
    if metadata.mergeable is False or str(metadata.mergeable_state or "").casefold() in {"dirty", "blocked", "conflicting"}:
        emit("metadata.merge_conflict_observed", evidence=[_e(EvidenceKind.METADATA, "GitHub mergeability indicates a conflict condition.", observed=str(metadata.mergeable_state or metadata.mergeable).casefold())])


def _detect_scope(snapshot: PullRequestSnapshot, emit) -> None:
    file_count = len(snapshot.files)
    if file_count >= VERY_LARGE_FILE_COUNT:
        emit("scope.very_large_file_count", evidence=[_e(EvidenceKind.FILE_COUNT, "Changed-file count reached the very-large threshold.", observed=str(file_count), expected=f">= {VERY_LARGE_FILE_COUNT}")])
    elif file_count >= LARGE_FILE_COUNT:
        emit("scope.large_file_count", evidence=[_e(EvidenceKind.FILE_COUNT, "Changed-file count reached the large threshold.", observed=str(file_count), expected=f">= {LARGE_FILE_COUNT}")])

    churn = snapshot.metadata.additions + snapshot.metadata.deletions
    if churn >= VERY_LARGE_TOTAL_CHURN:
        emit("scope.very_large_line_churn", evidence=[_e(EvidenceKind.LINE_COUNT, "Total additions and deletions reached the very-large threshold.", observed=str(churn), expected=f">= {VERY_LARGE_TOTAL_CHURN}")])
    elif churn >= LARGE_TOTAL_CHURN:
        emit("scope.large_line_churn", evidence=[_e(EvidenceKind.LINE_COUNT, "Total additions and deletions reached the large threshold.", observed=str(churn), expected=f">= {LARGE_TOTAL_CHURN}")])

    large_files = [file for file in snapshot.files if file.changes >= LARGE_INDIVIDUAL_FILE_CHANGE]
    if large_files:
        emit("scope.large_individual_file_change", _filenames(large_files), [_file_e(file, EvidenceKind.LINE_COUNT, "File change count reached the per-file threshold.", str(file.changes), f">= {LARGE_INDIVIDUAL_FILE_CHANGE}") for file in large_files])

    significant_areas = sorted(
        {area.value for file in snapshot.files for area in file.classification.areas if area.value not in SIGNIFICANT_AREA_EXCLUSIONS}
    )
    if len(significant_areas) >= BROAD_FUNCTIONAL_AREA_COUNT:
        emit("scope.broad_functional_change", evidence=[_e(EvidenceKind.CLASSIFICATION, "Significant functional areas were observed.", observed=", ".join(significant_areas), expected=f">= {BROAD_FUNCTIONAL_AREA_COUNT} areas")])


def _detect_classification(files: list[ChangedFile], emit) -> set[str]:
    auth = [file for file in files if FileArea.AUTHENTICATION in file.classification.areas]
    authz = [file for file in files if FileArea.AUTHORIZATION in file.classification.areas]
    migrations = [file for file in files if file.classification.primary_kind == FileKind.DATABASE_MIGRATION]
    api = [file for file in files if FileArea.API in file.classification.areas and file.classification.primary_kind not in API_EXCLUDED_KINDS]
    infra = [file for file in files if FileArea.INFRASTRUCTURE in file.classification.areas or file.classification.primary_kind == FileKind.INFRASTRUCTURE]
    ci_config = [file for file in files if FileArea.CI_CD in file.classification.areas or file.classification.primary_kind == FileKind.CI_CONFIGURATION]
    runtime_config = [file for file in files if _is_runtime_config(file)]

    for rule_id, matched, value in [
        ("authentication.paths_changed", auth, "authentication"),
        ("authorization.paths_changed", authz, "authorization"),
        ("database.migration_changed", migrations, "database_migration"),
        ("api.surface_changed", api, "api"),
        ("infrastructure.configuration_changed", infra, "infrastructure"),
        ("ci.configuration_changed", ci_config, "ci_cd"),
        ("configuration.runtime_configuration_changed", runtime_config, "runtime_configuration"),
    ]:
        if matched:
            emit(rule_id, _filenames(matched), [_file_e(file, EvidenceKind.CLASSIFICATION, f"{value.replace('_', ' ').title()} file changed.", value) for file in matched])

    return set(_filenames(auth + authz + migrations + api))


def _detect_testing(files: list[ChangedFile], has_tests: bool, sensitive_files: set[str], emit) -> None:
    production_files = [file for file in files if file.classification.primary_kind in PRODUCTION_RELEVANT_KINDS]
    if production_files and not has_tests:
        if sensitive_files:
            matched = [file for file in production_files if file.filename in sensitive_files]
            emit("testing.sensitive_change_without_test_files", _filenames(matched), [_file_e(file, EvidenceKind.CLASSIFICATION, "Sensitive production-relevant file changed without changed test files.", file.classification.primary_kind.value) for file in matched])
        else:
            emit("testing.production_change_without_test_files", _filenames(production_files), [_file_e(file, EvidenceKind.CLASSIFICATION, "Production-relevant file changed without changed test files.", file.classification.primary_kind.value) for file in production_files])

    removed_tests = [file for file in files if file.classification.primary_kind == FileKind.TEST and file.status in {"removed", "deleted"}]
    if removed_tests:
        emit("testing.test_files_deleted", _filenames(removed_tests), [_file_e(file, EvidenceKind.FILE_PATH, "Test file was removed.", file.status) for file in removed_tests])
    elif has_tests:
        test_files = [file for file in files if file.classification.primary_kind == FileKind.TEST]
        emit("testing.test_files_changed", _filenames(test_files), [_file_e(file, EvidenceKind.CLASSIFICATION, "Test file changed.", "test") for file in test_files])

    if files and all(file.classification.primary_kind in {FileKind.TEST, FileKind.DOCUMENTATION} for file in files):
        emit("testing.only_test_or_documentation_changes", _filenames(files), [_file_e(file, EvidenceKind.CLASSIFICATION, "File is classified as test or documentation.", file.classification.primary_kind.value) for file in files])


def _detect_ci(snapshot: PullRequestSnapshot, emit) -> None:
    ci = snapshot.ci
    if ci.state == CiState.FAILING:
        emit("ci.failing", evidence=[_e(EvidenceKind.CI_STATE, "Normalized CI state is failing.", observed=ci.state.value)])
    if ci.state == CiState.PENDING:
        emit("ci.pending", evidence=[_e(EvidenceKind.CI_STATE, "Normalized CI state is pending.", observed=ci.state.value)])
    if ci.visibility == CiVisibility.UNAVAILABLE:
        emit("ci.unavailable", evidence=[_e(EvidenceKind.CI_VISIBILITY, "CI visibility is unavailable.", observed=ci.visibility.value)])
    else:
        if ci.state == CiState.MISSING and ci.visibility == CiVisibility.COMPLETE:
            emit("ci.missing", evidence=[_e(EvidenceKind.CI_STATE, "No check runs or commit-status contexts were observed for the current head SHA.", observed=ci.state.value)])
        if ci.visibility == CiVisibility.PARTIAL:
            emit("ci.partial_visibility", evidence=[_e(EvidenceKind.CI_VISIBILITY, "CI visibility is partial.", observed=ci.visibility.value)])
        if ci.state == CiState.UNKNOWN and (ci.check_runs or ci.commit_statuses):
            emit("ci.unknown_outcome", evidence=[_e(EvidenceKind.CI_STATE, "Observed CI records could not be classified reliably.", observed=ci.state.value)])


def _detect_dependencies(files: list[ChangedFile], emit) -> None:
    manifests = [file for file in files if file.classification.primary_kind == FileKind.DEPENDENCY_MANIFEST]
    lockfiles = [file for file in files if file.classification.primary_kind == FileKind.DEPENDENCY_LOCKFILE]
    lockfile_names = {file.filename.rsplit("/", 1)[-1].casefold() for file in lockfiles}

    if manifests:
        emit("dependencies.manifest_changed", _filenames(manifests), [_file_e(file, EvidenceKind.CLASSIFICATION, "Dependency manifest file changed.", "dependency_manifest") for file in manifests])
    if lockfiles:
        emit("dependencies.lockfile_changed", _filenames(lockfiles), [_file_e(file, EvidenceKind.CLASSIFICATION, "Dependency lockfile changed.", "dependency_lockfile") for file in lockfiles])

    missing_lock_evidence: list[SignalEvidence] = []
    missing_lock_files: list[str] = []
    for manifest in manifests:
        name = manifest.filename.rsplit("/", 1)[-1].casefold()
        expected = DEPENDENCY_LOCKFILES_BY_MANIFEST.get(name)
        if expected and not (expected & lockfile_names):
            missing_lock_files.append(manifest.filename)
            missing_lock_evidence.append(_file_e(manifest, EvidenceKind.FILE_PATH, "Manifest changed without a companion lockfile from a known convention.", name, ", ".join(sorted(expected))))
    if missing_lock_files:
        emit("dependencies.manifest_without_lockfile", missing_lock_files, missing_lock_evidence)

    non_lock_production = [
        file for file in files
        if file.classification.primary_kind in PRODUCTION_RELEVANT_KINDS
        and file.classification.primary_kind != FileKind.DEPENDENCY_LOCKFILE
    ]
    if lockfiles and not manifests and not non_lock_production:
        emit("dependencies.lockfile_only_change", _filenames(lockfiles), [_file_e(file, EvidenceKind.CLASSIFICATION, "Dependency lockfile changed without manifest or production file changes.", "dependency_lockfile") for file in lockfiles])


def _detect_patch_signals(files: list[ChangedFile], emit, warnings: list[str]) -> set[str]:
    migration_patchless_files: set[str] = set()

    for file in files:
        parsed = parse_patch(file.patch)
        warnings.extend(parsed.warnings)
        if file.classification.primary_kind == FileKind.DATABASE_MIGRATION and file.patch is None:
            migration_patchless_files.add(file.filename)
            emit("database.migration_without_patch_visibility", [file.filename], [_file_e(file, EvidenceKind.COMPLETENESS, "Patch-level migration inspection was unavailable.", "missing_patch")])
        if not parsed.lines or file.classification.primary_kind in PATCH_SCAN_EXCLUDED_KINDS:
            continue

        added_lines = [line for line in parsed.lines if line.kind == PatchLineKind.ADDED]
        _scan_added_line_patterns(file, added_lines, emit)
        _scan_empty_exception(file, parsed, emit)
        if _is_migration_patch_target(file):
            _scan_migration_sql(file, added_lines, emit)

    return migration_patchless_files


def _scan_added_line_patterns(file: ChangedFile, added_lines, emit) -> None:
    is_test_file = file.classification.primary_kind == FileKind.TEST
    if not is_test_file:
        for label, pattern in DEBUG_PATTERNS:
            if any(_looks_like_code(line.content) and pattern.search(line.content) for line in added_lines):
                emit("code_quality.debug_statement_added", [file.filename], [_file_e(file, EvidenceKind.PATCH_PATTERN, "Debug statement pattern detected in added patch content.", label)])
                break
    for line in added_lines:
        if TODO_PATTERN.search(line.content):
            emit("code_quality.todo_or_fixme_added", [file.filename], [_file_e(file, EvidenceKind.PATCH_PATTERN, "TODO or FIXME comment marker detected in added patch content.", "todo_or_fixme")])
            break
    if is_test_file:
        for label, pattern in TEST_SKIP_PATTERNS:
            if any(pattern.search(line.content) for line in added_lines):
                emit("testing.test_skip_added", [file.filename], [_file_e(file, EvidenceKind.PATCH_PATTERN, "Test skip pattern detected in added patch content.", label)])
                break
    for label, pattern in SUPPRESSION_PATTERNS:
        if any(pattern.search(line.content) for line in added_lines):
            emit("code_quality.lint_or_type_suppression_added", [file.filename], [_file_e(file, EvidenceKind.PATCH_PATTERN, "Lint or type suppression pattern detected in added patch content.", label)])
            break
    for line in added_lines:
        secret_match = SECRET_ASSIGNMENT_PATTERN.search(line.content)
        if secret_match and not _is_safe_secret_reference(line.content, secret_match.group("value")):
            emit("security.credential_like_literal_added", [file.filename], [_file_e(file, EvidenceKind.PATCH_PATTERN, "A credential-like literal assignment pattern was detected in added patch content.", _secret_identifier_category(secret_match.group("name")))])
            break
    for label, pattern in SECURITY_DISABLE_PATTERNS:
        if any(pattern.search(line.content) for line in added_lines):
            emit("security.security_control_disabled_hint", [file.filename], [_file_e(file, EvidenceKind.PATCH_PATTERN, "Security-control disable pattern detected in added patch content.", label)])
            break


def _scan_empty_exception(file: ChangedFile, parsed, emit) -> None:
    if file.classification.language != FileLanguage.PYTHON:
        return
    for lines in added_lines_by_hunk(parsed).values():
        for index, line in enumerate(lines[:-1]):
            if re.match(r"^\s*except(\s+Exception)?\s*:\s*$", line.content):
                for next_line in lines[index + 1:index + 4]:
                    if re.match(r"^\s*pass\s*(#.*)?$", next_line.content):
                        emit("code_quality.empty_exception_handler_added", [file.filename], [_file_e(file, EvidenceKind.PATCH_PATTERN, "Exception handler followed by pass detected in added patch content.", "empty_exception_handler")])
                        return


def _scan_migration_sql(file: ChangedFile, added_lines, emit) -> None:
    for label, pattern in DESTRUCTIVE_SQL_PATTERNS:
        if any(pattern.search(line.content) for line in added_lines):
            emit("database.destructive_migration_hint", [file.filename], [_file_e(file, EvidenceKind.PATCH_PATTERN, "Destructive SQL pattern category detected in added migration patch content.", label)])
            break


def _detect_generated_and_opaque(files: list[ChangedFile], migration_patchless_files: set[str], emit) -> None:
    generated = [file for file in files if file.classification.primary_kind == FileKind.GENERATED]
    if generated:
        emit("generated_content.generated_files_changed", _filenames(generated), [_file_e(file, EvidenceKind.CLASSIFICATION, "Generated file changed.", "generated") for file in generated])
        generated_churn = sum(file.changes for file in generated)
        if generated_churn >= LARGE_GENERATED_CHURN or len(generated) >= LARGE_GENERATED_FILE_COUNT:
            emit("generated_content.large_generated_change", _filenames(generated), [_e(EvidenceKind.LINE_COUNT, "Generated file count or churn reached the configured threshold.", observed=f"files={len(generated)}, changes={generated_churn}")])

    opaque = [
        file for file in files
        if (file.classification.primary_kind == FileKind.BINARY or file.patch is None)
        and file.filename not in migration_patchless_files
    ]
    if opaque:
        emit("completeness.opaque_files_changed", _filenames(opaque), [_file_e(file, EvidenceKind.COMPLETENESS, "Binary or patchless file changed.", file.classification.primary_kind.value if file.patch is not None else "missing_patch") for file in opaque])


def _detect_renames(files: list[ChangedFile], emit) -> None:
    for file in files:
        previous = file.previous_classification
        if not previous or previous == file.classification:
            continue
        previous_areas = {area.value for area in previous.areas}
        current_areas = {area.value for area in file.classification.areas}
        sensitive_added = sorted((current_areas & SENSITIVE_RENAME_AREAS) - (previous_areas & SENSITIVE_RENAME_AREAS))
        if sensitive_added:
            emit("rename.file_moved_into_sensitive_area", [file.filename], [_rename_e(file, "File moved into sensitive classification area.", ",".join(sensitive_added), previous.primary_kind.value)])
        if previous.primary_kind == FileKind.TEST and file.classification.primary_kind != FileKind.TEST:
            emit("rename.file_moved_out_of_test_area", [file.filename], [_rename_e(file, "File moved out of test classification.", file.classification.primary_kind.value, "test")])
        if previous.primary_kind != FileKind.GENERATED and file.classification.primary_kind == FileKind.GENERATED:
            emit("rename.file_moved_into_generated_area", [file.filename], [_rename_e(file, "File moved into generated classification.", "generated", previous.primary_kind.value)])


def _detect_completeness(snapshot: PullRequestSnapshot, migration_patchless_files: set[str], emit) -> None:
    if snapshot.completeness.missing_patch_count and len(migration_patchless_files) < snapshot.completeness.missing_patch_count:
        emit("completeness.patch_coverage_incomplete", evidence=[_e(EvidenceKind.COMPLETENESS, "Snapshot reports missing GitHub patch data.", observed=str(snapshot.completeness.missing_patch_count))])
    if not snapshot.completeness.files_complete:
        emit("completeness.file_collection_incomplete", evidence=[_e(EvidenceKind.COMPLETENESS, "Changed-file collection is incomplete.", observed="files_complete=false")])
    if not snapshot.completeness.commits_complete:
        emit("completeness.commit_collection_incomplete", evidence=[_e(EvidenceKind.COMPLETENESS, "Commit collection is incomplete.", observed="commits_complete=false")])


def _build_signals(accumulators: dict[str, SignalAccumulator]) -> list[ReviewSignal]:
    signals: list[ReviewSignal] = []
    for rule_id, accumulator in accumulators.items():
        evidence = [_evidence_from_key(key) for key in sorted(accumulator.evidence, key=_evidence_sort_key)]
        limitations = accumulator.rule.limitations + tuple(sorted(accumulator.extra_limitations))
        if len(evidence) > MAX_EVIDENCE_ITEMS_PER_SIGNAL:
            evidence = evidence[:MAX_EVIDENCE_ITEMS_PER_SIGNAL]
            limitations = tuple(limitations) + ("Additional evidence was omitted after the per-signal evidence cap.",)
        affected_files = sorted(accumulator.affected_files, key=lambda value: (value.casefold(), value))
        signals.append(
            ReviewSignal(
                id=rule_id,
                rule_id=rule_id,
                title=accumulator.rule.title,
                description=accumulator.rule.description,
                category=accumulator.rule.category,
                severity=accumulator.rule.severity,
                scope=accumulator.rule.scope,
                affected_files=affected_files,
                evidence=evidence,
                limitations=sorted(set(limitations)),
                tags=sorted(set(accumulator.rule.tags)),
            )
        )
    return sorted(
        signals,
        key=lambda signal: (
            SEVERITY_ORDER[signal.severity],
            CATEGORY_ORDER[signal.category],
            signal.rule_id,
            signal.id,
        ),
    )


def _is_runtime_config(file: ChangedFile) -> bool:
    name = file.filename.rsplit("/", 1)[-1].casefold()
    if name in {".editorconfig", ".nvmrc", ".python-version"}:
        return False
    return (
        name in RUNTIME_CONFIG_FILENAMES
        or name.startswith(".env.")
        or file.filename.casefold().endswith("/config/settings.py")
        or file.filename.casefold().endswith("/core/config.py")
    )


def _is_migration_patch_target(file: ChangedFile) -> bool:
    return file.classification.primary_kind == FileKind.DATABASE_MIGRATION


def _looks_like_code(line: str) -> bool:
    stripped = line.lstrip()
    return not stripped.startswith(("#", "//", "*", "<!--"))


def _is_safe_secret_reference(line: str, value: str) -> bool:
    normalized = value.strip().strip("\"'").casefold()
    return (
        SAFE_REFERENCE_PATTERN.search(line) is not None
        or normalized == ""
        or normalized in SECRET_PLACEHOLDERS
        or normalized.startswith("<")
        or normalized.startswith("${{")
    )


def _secret_identifier_category(name: str) -> str:
    normalized = name.replace("-", "_").casefold()
    if "password" in normalized or normalized == "passwd":
        return "password_like_literal"
    if "token" in normalized:
        return "token_like_literal"
    if "key" in normalized:
        return "key_like_literal"
    if "secret" in normalized:
        return "secret_like_literal"
    return "credential_like_literal"


def _filenames(files: list[ChangedFile]) -> list[str]:
    return sorted({file.filename for file in files}, key=lambda value: (value.casefold(), value))


def _e(kind: EvidenceKind, message: str, observed: str | None = None, expected: str | None = None, file: str | None = None) -> SignalEvidence:
    return SignalEvidence(kind=kind, message=message, file=file, observed_value=observed, expected_context=expected)


def _file_e(file: ChangedFile, kind: EvidenceKind, message: str, observed: str | None = None, expected: str | None = None) -> SignalEvidence:
    return _e(kind, message, observed, expected, file.filename)


def _rename_e(file: ChangedFile, message: str, observed: str, previous: str) -> SignalEvidence:
    return _e(EvidenceKind.RENAME_TRANSITION, message, observed, f"previous={previous}", file.filename)


def _evidence_key(evidence: SignalEvidence) -> tuple[str, str, str, str, str]:
    return (
        evidence.kind.value,
        evidence.message,
        evidence.file or "",
        evidence.observed_value or "",
        evidence.expected_context or "",
    )


def _evidence_from_key(key: tuple[str, str, str, str, str]) -> SignalEvidence:
    kind, message, file, observed, expected = key
    return SignalEvidence(
        kind=EvidenceKind(kind),
        message=message,
        file=file or None,
        observed_value=observed or None,
        expected_context=expected or None,
    )


def _evidence_sort_key(key: tuple[str, str, str, str, str]) -> tuple[str, str, str, str, str]:
    kind, message, file, observed, _expected = key
    return kind, file.casefold(), file, message, observed
