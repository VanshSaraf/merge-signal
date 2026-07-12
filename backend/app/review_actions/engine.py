from app.domain.pull_request import CiState, CiVisibility, PullRequestSnapshot
from app.domain.review_action import ReviewAction, ReviewActionSummary
from app.domain.review_signal import ReviewSignal
from app.domain.scoring import ConfidenceComponentStatus
from app.review_actions.ordering import action_sort_key, unique_file_ordered, unique_sorted
from app.review_actions.rules import RULE_BY_ID
from app.review_actions.summary import summarize_review_actions

CI_VISIBILITY_SIGNAL_RULE_IDS = frozenset({
    "ci.missing",
    "ci.unavailable",
    "ci.partial_visibility",
    "ci.unknown_outcome",
})

INCOMPLETE_EVIDENCE_SIGNAL_RULE_IDS = frozenset({
    "completeness.file_collection_incomplete",
    "completeness.commit_collection_incomplete",
    "completeness.patch_coverage_incomplete",
})

LARGE_SCOPE_SIGNAL_RULE_IDS = frozenset({
    "scope.large_file_count",
    "scope.very_large_file_count",
    "scope.large_line_churn",
    "scope.very_large_line_churn",
    "scope.large_individual_file_change",
    "scope.broad_functional_change",
})

CODE_QUALITY_SIGNAL_RULE_IDS = frozenset({
    "code_quality.debug_statement_added",
    "code_quality.todo_or_fixme_added",
    "code_quality.lint_or_type_suppression_added",
    "code_quality.empty_exception_handler_added",
})

GENERATED_OR_OPAQUE_SIGNAL_RULE_IDS = frozenset({
    "generated_content.generated_files_changed",
    "generated_content.large_generated_change",
    "completeness.opaque_files_changed",
})

SENSITIVE_RENAME_SIGNAL_RULE_IDS = frozenset({
    "rename.file_moved_into_sensitive_area",
    "rename.file_moved_out_of_test_area",
})

ACTION_LIMITATION = "Actions describe what to verify next; they do not prescribe code changes."


def build_review_actions(snapshot: PullRequestSnapshot) -> tuple[list[ReviewAction], ReviewActionSummary]:
    signals_by_rule = _signals_by_rule(snapshot.signals)
    reasons_by_rule = _reasons_by_rule(snapshot)
    ranked_positions = {file.path: file.rank for file in snapshot.ranked_files}
    actions = [
        *_mergeability_actions(signals_by_rule, reasons_by_rule, ranked_positions),
        *_ci_actions(snapshot, signals_by_rule, reasons_by_rule, ranked_positions),
        *_security_actions(signals_by_rule, reasons_by_rule, ranked_positions),
        *_database_actions(signals_by_rule, reasons_by_rule, ranked_positions),
        *_testing_actions(signals_by_rule, reasons_by_rule, ranked_positions),
        *_medium_signal_actions(signals_by_rule, ranked_positions),
        *_incomplete_evidence_actions(snapshot, signals_by_rule, reasons_by_rule, ranked_positions),
        *_low_signal_actions(signals_by_rule, ranked_positions),
        *_baseline_file_review_action(snapshot, ranked_positions),
    ]
    deduplicated = _deduplicate_actions(actions)
    ordered = sorted(deduplicated, key=action_sort_key)
    return ordered, summarize_review_actions(ordered)


def _mergeability_actions(
    signals_by_rule: dict[str, list[ReviewSignal]],
    reasons_by_rule: dict[str, list[str]],
    ranked_positions: dict[str, int],
) -> list[ReviewAction]:
    if "metadata.merge_conflict_observed" not in signals_by_rule and "readiness.blocked.merge_conflict" not in reasons_by_rule:
        return []
    return [
        _action(
            "action.resolve_merge_conflict",
            signals_by_rule.get("metadata.merge_conflict_observed", []),
            reasons_by_rule.get("readiness.blocked.merge_conflict", []),
            ["GitHub reported mergeability data consistent with a conflict condition."],
            ranked_positions,
        )
    ]


def _ci_actions(
    snapshot: PullRequestSnapshot,
    signals_by_rule: dict[str, list[ReviewSignal]],
    reasons_by_rule: dict[str, list[str]],
    ranked_positions: dict[str, int],
) -> list[ReviewAction]:
    actions: list[ReviewAction] = []
    ci_failing = snapshot.ci.state == CiState.FAILING or "ci.failing" in signals_by_rule or "readiness.blocked.ci_failing" in reasons_by_rule
    if ci_failing:
        actions.append(
            _action(
                "action.inspect_failing_ci",
                signals_by_rule.get("ci.failing", []),
                reasons_by_rule.get("readiness.blocked.ci_failing", []),
                [f"Observed CI state: {snapshot.ci.state.value}.", "MergeSignal does not infer which checks are required."],
                ranked_positions,
            )
        )
    elif snapshot.ci.state == CiState.PENDING or "ci.pending" in signals_by_rule:
        actions.append(
            _action(
                "action.await_pending_ci",
                signals_by_rule.get("ci.pending", []),
                reasons_by_rule.get("readiness.not_ready.ci_pending", []),
                [f"Observed CI state: {snapshot.ci.state.value}."],
                ranked_positions,
            )
        )

    visibility_signals = [signal for rule_id in CI_VISIBILITY_SIGNAL_RULE_IDS for signal in signals_by_rule.get(rule_id, [])]
    if (
        snapshot.ci.visibility in {CiVisibility.UNAVAILABLE, CiVisibility.PARTIAL}
        or snapshot.ci.state in {CiState.MISSING, CiState.UNKNOWN}
        or visibility_signals
    ):
        actions.append(
            _action(
                "action.investigate_ci_visibility",
                visibility_signals,
                [
                    *reasons_by_rule.get("readiness.not_ready.ci_unavailable", []),
                    *reasons_by_rule.get("readiness.caution.ci_missing", []),
                    *reasons_by_rule.get("readiness.caution.ci_unknown", []),
                    *reasons_by_rule.get("readiness.caution.ci_partial_visibility", []),
                ],
                [f"Observed CI state: {snapshot.ci.state.value}.", f"Observed CI visibility: {snapshot.ci.visibility.value}."],
                ranked_positions,
            )
        )
    return actions


def _security_actions(
    signals_by_rule: dict[str, list[ReviewSignal]],
    reasons_by_rule: dict[str, list[str]],
    ranked_positions: dict[str, int],
) -> list[ReviewAction]:
    return _actions_when_traceable(
        (
            (
                "action.verify_credential_like_literal",
                signals_by_rule.get("security.credential_like_literal_added", []),
                reasons_by_rule.get("readiness.not_ready.credential_like_literal", []),
                ["A credential-like literal pattern was observed; suspected values and full source lines are omitted."],
            ),
            (
                "action.verify_security_control_setting",
                signals_by_rule.get("security.security_control_disabled_hint", []),
                reasons_by_rule.get("readiness.not_ready.security_control_disabled", []),
                ["A security-control disabling pattern was observed; raw patch lines are omitted."],
            ),
        ),
        ranked_positions,
    )


def _database_actions(
    signals_by_rule: dict[str, list[ReviewSignal]],
    reasons_by_rule: dict[str, list[str]],
    ranked_positions: dict[str, int],
) -> list[ReviewAction]:
    return _actions_when_traceable(
        (
            (
                "action.inspect_destructive_migration",
                signals_by_rule.get("database.destructive_migration_hint", []),
                reasons_by_rule.get("readiness.caution.destructive_migration_hint", []),
                ["A destructive migration pattern was observed in GitHub-provided patch evidence."],
            ),
            (
                "action.inspect_migration_without_patch",
                signals_by_rule.get("database.migration_without_patch_visibility", []),
                [],
                ["Patch-level migration inspection was unavailable for one or more migration files."],
            ),
        ),
        ranked_positions,
    )


def _testing_actions(
    signals_by_rule: dict[str, list[ReviewSignal]],
    reasons_by_rule: dict[str, list[str]],
    ranked_positions: dict[str, int],
) -> list[ReviewAction]:
    return _actions_when_traceable(
        (
            (
                "action.review_sensitive_change_tests",
                signals_by_rule.get("testing.sensitive_change_without_test_files", []),
                reasons_by_rule.get("readiness.caution.sensitive_change_without_tests", []),
                ["No test files changed in this PR."],
            ),
            (
                "action.review_production_change_tests",
                signals_by_rule.get("testing.production_change_without_test_files", []),
                [],
                ["No test files changed in this PR."],
            ),
            (
                "action.review_deleted_tests",
                signals_by_rule.get("testing.test_files_deleted", []),
                reasons_by_rule.get("readiness.caution.test_files_deleted", []),
                ["One or more changed files classified as tests were removed."],
            ),
        ),
        ranked_positions,
    )


def _medium_signal_actions(
    signals_by_rule: dict[str, list[ReviewSignal]],
    ranked_positions: dict[str, int],
) -> list[ReviewAction]:
    large_scope_signals = [signal for rule_id in LARGE_SCOPE_SIGNAL_RULE_IDS for signal in signals_by_rule.get(rule_id, [])]
    sensitive_rename_signals = [signal for rule_id in SENSITIVE_RENAME_SIGNAL_RULE_IDS for signal in signals_by_rule.get(rule_id, [])]
    dependency_signals = [*signals_by_rule.get("dependencies.manifest_changed", []), *signals_by_rule.get("dependencies.manifest_without_lockfile", [])]
    return _actions_when_traceable(
        (
            ("action.review_runtime_configuration", signals_by_rule.get("configuration.runtime_configuration_changed", []), [], ["Runtime configuration paths changed."]),
            ("action.review_dependency_manifest", dependency_signals, [], ["Dependency manifest evidence was observed."]),
            ("action.review_infrastructure_change", signals_by_rule.get("infrastructure.configuration_changed", []), [], ["Infrastructure or deployment configuration paths changed."]),
            ("action.review_large_change_scope", large_scope_signals, [], ["Large or broad change-scope evidence was observed."]),
            ("action.review_sensitive_rename", sensitive_rename_signals, [], ["A rename transition into a sensitive area or out of test classification was observed."]),
        ),
        ranked_positions,
    )


def _incomplete_evidence_actions(
    snapshot: PullRequestSnapshot,
    signals_by_rule: dict[str, list[ReviewSignal]],
    reasons_by_rule: dict[str, list[str]],
    ranked_positions: dict[str, int],
) -> list[ReviewAction]:
    incomplete_signals = [signal for rule_id in INCOMPLETE_EVIDENCE_SIGNAL_RULE_IDS for signal in signals_by_rule.get(rule_id, [])]
    patch_partial = _component_status(snapshot, "patch_visibility") == ConfidenceComponentStatus.PARTIAL
    if snapshot.completeness.files_complete and snapshot.completeness.commits_complete and not patch_partial and not incomplete_signals:
        return []
    evidence: list[str] = []
    if not snapshot.completeness.files_complete:
        evidence.append("Changed-file collection is incomplete.")
    if not snapshot.completeness.commits_complete:
        evidence.append("Commit collection is incomplete.")
    if patch_partial or snapshot.completeness.missing_patch_count > 0:
        evidence.append(f"Missing patch count: {snapshot.completeness.missing_patch_count}.")
    return [
        _action(
            "action.inspect_incomplete_evidence",
            incomplete_signals,
            [
                *reasons_by_rule.get("readiness.not_ready.file_collection_incomplete", []),
                *reasons_by_rule.get("readiness.caution.patch_visibility_partial", []),
                *reasons_by_rule.get("readiness.caution.commit_collection_incomplete", []),
            ],
            evidence,
            ranked_positions,
        )
    ]


def _low_signal_actions(
    signals_by_rule: dict[str, list[ReviewSignal]],
    ranked_positions: dict[str, int],
) -> list[ReviewAction]:
    code_quality_signals = [signal for rule_id in CODE_QUALITY_SIGNAL_RULE_IDS for signal in signals_by_rule.get(rule_id, [])]
    generated_signals = [signal for rule_id in GENERATED_OR_OPAQUE_SIGNAL_RULE_IDS for signal in signals_by_rule.get(rule_id, [])]
    return _actions_when_traceable(
        (
            ("action.review_code_quality_hints", code_quality_signals, [], ["Code-quality hint signals were observed."]),
            ("action.review_generated_or_opaque_changes", generated_signals, [], ["Generated, large generated, opaque, or patchless-file evidence was observed."]),
        ),
        ranked_positions,
    )


def _actions_when_traceable(
    specs: tuple[tuple[str, list[ReviewSignal], list[str], list[str]], ...],
    ranked_positions: dict[str, int],
) -> list[ReviewAction]:
    return [
        _action(rule_id, signals, readiness_rule_ids, evidence, ranked_positions)
        for rule_id, signals, readiness_rule_ids, evidence in specs
        if signals or readiness_rule_ids
    ]


def _baseline_file_review_action(
    snapshot: PullRequestSnapshot,
    ranked_positions: dict[str, int],
) -> list[ReviewAction]:
    if not snapshot.ranked_files:
        return []
    files = [file.path for file in sorted(snapshot.ranked_files, key=lambda file: file.rank)[:5]]
    return [
        _action(
            "action.review_highest_priority_files",
            [],
            [],
            ["Top ranked files: " + ", ".join(files), "Lower-ranked files must not be ignored."],
            ranked_positions,
            affected_files=files,
        )
    ]


def _action(
    rule_id: str,
    signals: list[ReviewSignal],
    readiness_rule_ids: list[str],
    evidence: list[str],
    ranked_positions: dict[str, int],
    *,
    affected_files: list[str] | None = None,
) -> ReviewAction:
    rule = RULE_BY_ID[rule_id]
    files = affected_files if affected_files is not None else [path for signal in signals for path in signal.affected_files]
    return ReviewAction(
        id=rule.rule_id,
        rule_id=rule.rule_id,
        title=rule.title,
        description=rule.description,
        priority=rule.priority,
        category=rule.category,
        affected_files=unique_file_ordered(files, ranked_positions),
        related_signal_ids=unique_sorted([signal.id for signal in signals]),
        related_readiness_rule_ids=unique_sorted(readiness_rule_ids),
        evidence=unique_sorted(evidence),
        limitations=unique_sorted([*rule.limitations, ACTION_LIMITATION]),
    )


def _deduplicate_actions(actions: list[ReviewAction]) -> list[ReviewAction]:
    by_rule: dict[str, ReviewAction] = {}
    for action in actions:
        if not _has_evidence(action):
            continue
        existing = by_rule.get(action.rule_id)
        if existing is None:
            by_rule[action.rule_id] = action
            continue
        by_rule[action.rule_id] = action.model_copy(
            update={
                "affected_files": unique_file_ordered([*existing.affected_files, *action.affected_files], {}),
                "related_signal_ids": unique_sorted([*existing.related_signal_ids, *action.related_signal_ids]),
                "related_readiness_rule_ids": unique_sorted([*existing.related_readiness_rule_ids, *action.related_readiness_rule_ids]),
                "evidence": unique_sorted([*existing.evidence, *action.evidence]),
            }
        )
    return list(by_rule.values())


def _has_evidence(action: ReviewAction) -> bool:
    return bool(action.related_signal_ids or action.related_readiness_rule_ids or action.affected_files or action.evidence)


def _signals_by_rule(signals: list[ReviewSignal]) -> dict[str, list[ReviewSignal]]:
    grouped: dict[str, list[ReviewSignal]] = {}
    for signal in signals:
        grouped.setdefault(signal.rule_id, []).append(signal)
    return {
        rule_id: sorted(items, key=lambda signal: signal.id)
        for rule_id, items in sorted(grouped.items(), key=lambda item: item[0])
    }


def _reasons_by_rule(snapshot: PullRequestSnapshot) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for reason in snapshot.merge_readiness.reasons:
        grouped.setdefault(reason.rule_id, []).append(reason.rule_id)
    return {rule_id: unique_sorted(items) for rule_id, items in sorted(grouped.items(), key=lambda item: item[0])}


def _component_status(snapshot: PullRequestSnapshot, component_id: str) -> ConfidenceComponentStatus | None:
    for component in snapshot.evidence_confidence.components:
        if component.id == component_id:
            return component.status
    return None
