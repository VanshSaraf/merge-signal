from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.file_classification import FileKind
from app.domain.pull_request import (
    ChangedFile,
    CiCompleteness,
    CiState,
    CiVisibility,
    GitHubRateLimit,
    PullRequestAuthor,
    PullRequestBranch,
    PullRequestCi,
    PullRequestCommit,
    PullRequestMetadata,
    PullRequestReference,
    PullRequestSnapshot,
    SnapshotCompleteness,
)
from app.domain.review_signal import EvidenceKind, ReviewSignalSummary, SignalCategory, SignalScope, SignalSeverity
from app.services.file_classifier import classify_changed_files
from app.signals.engine import analyze_snapshot_signals
from app.signals.patch_scanner import PatchLineKind, parse_patch


BASE_TIME = datetime(2026, 7, 3, 10, 0, tzinfo=UTC)


def changed_file(
    filename: str,
    *,
    status: str = "modified",
    changes: int = 10,
    patch: str | None = "@@ -1 +1 @@\n-old\n+new",
    previous_filename: str | None = None,
) -> ChangedFile:
    return ChangedFile(
        filename=filename,
        status=status,
        additions=max(changes, 0),
        deletions=0,
        changes=changes,
        patch=patch,
        previous_filename=previous_filename,
        blob_url=None,
    )


def snapshot(
    files: list[ChangedFile],
    *,
    body: str | None = "Useful context",
    draft: bool = False,
    commit_count: int = 1,
    additions: int | None = None,
    deletions: int = 0,
    mergeable: bool | None = None,
    mergeable_state: str | None = None,
    ci_state: CiState = CiState.PASSING,
    ci_visibility: CiVisibility = CiVisibility.COMPLETE,
    files_complete: bool = True,
    commits_complete: bool = True,
) -> PullRequestSnapshot:
    classified_files, classification_summary = classify_changed_files(files)
    additions = sum(file.additions for file in classified_files) if additions is None else additions
    return PullRequestSnapshot(
        reference=PullRequestReference(
            owner="octocat",
            repository="Hello-World",
            pull_number=42,
            canonical_url="https://github.com/octocat/Hello-World/pull/42",
        ),
        metadata=PullRequestMetadata(
            number=42,
            title="Signal fixture",
            body=body,
            state="open",
            draft=draft,
            html_url="https://github.com/octocat/Hello-World/pull/42",
            author=PullRequestAuthor(login="octocat", avatar_url=None, html_url=None),
            base_branch=PullRequestBranch(ref="main", sha="base", repository_full_name="octocat/Hello-World"),
            head_branch=PullRequestBranch(ref="feature", sha="head", repository_full_name="octocat/Hello-World"),
            head_sha="head",
            created_at=BASE_TIME,
            updated_at=BASE_TIME,
            closed_at=None,
            merged_at=None,
            additions=additions,
            deletions=deletions,
            changed_files=len(classified_files),
            commit_count=commit_count,
            mergeable=mergeable,
            mergeable_state=mergeable_state,
            labels=[],
        ),
        files=classified_files,
        commits=[
            PullRequestCommit(
                sha="commit",
                message="Fixture",
                html_url=None,
                author_login=None,
                author_name=None,
                authored_at=BASE_TIME,
                committed_at=BASE_TIME,
            )
        ],
        ci=PullRequestCi(
            state=ci_state,
            visibility=ci_visibility,
            check_runs=[] if ci_state == CiState.MISSING else [],
            commit_statuses=[],
            total_check_runs=0,
            total_status_contexts=0,
            passing_count=1 if ci_state == CiState.PASSING else 0,
            failing_count=1 if ci_state == CiState.FAILING else 0,
            pending_count=1 if ci_state == CiState.PENDING else 0,
            neutral_count=0,
            skipped_count=0,
            warnings=[],
            fetched_at=BASE_TIME,
            completeness=CiCompleteness(
                check_runs_complete=ci_visibility != CiVisibility.UNAVAILABLE,
                commit_statuses_complete=ci_visibility == CiVisibility.COMPLETE,
                check_run_pages_fetched=1,
                commit_status_pages_fetched=1,
                raw_status_record_count=0,
                unique_status_context_count=0,
                warnings=[],
            ),
            rate_limit=None,
        ),
        classification_summary=classification_summary,
        completeness=SnapshotCompleteness(
            files_complete=files_complete,
            commits_complete=commits_complete,
            missing_patch_count=sum(1 for file in classified_files if file.patch is None),
            warnings=[],
        ),
        fetched_at=BASE_TIME,
        rate_limit=GitHubRateLimit(limit=None, remaining=None, used=None, resource=None, reset_at=None),
    )


def rule_ids(result) -> list[str]:
    return [signal.rule_id for signal in result.signals]


def test_signal_domain_values_and_strict_validation() -> None:
    assert [severity.value for severity in SignalSeverity] == ["info", "low", "medium", "high"]
    assert "security" in [category.value for category in SignalCategory]
    assert [scope.value for scope in SignalScope] == ["pull_request", "file_set", "file", "ci_surface", "snapshot"]
    assert "patch_pattern" in [kind.value for kind in EvidenceKind]
    assert ReviewSignalSummary(
        total_signals=0,
        counts_by_severity=[],
        counts_by_category=[],
        files_with_signals=[],
        high_attention_files=[],
        patch_based_signal_count=0,
        metadata_signal_count=0,
        ci_signal_count=0,
        warnings=[],
        rules_version="v1",
    ).rules_version == "v1"
    with pytest.raises(ValidationError):
        ReviewSignalSummary(
            total_signals=-1,
            counts_by_severity=[],
            counts_by_category=[],
            files_with_signals=[],
            high_attention_files=[],
            patch_based_signal_count=0,
            metadata_signal_count=0,
            ci_signal_count=0,
            warnings=[],
            rules_version="v1",
        )


def test_metadata_scope_and_ordering_signals() -> None:
    files = [changed_file(f"backend/services/file_{index}.py", changes=600) for index in range(80)]
    result = analyze_snapshot_signals(
        snapshot(
            files,
            body="   ",
            draft=True,
            commit_count=20,
            additions=3000,
            mergeable=False,
            ci_state=CiState.FAILING,
            ci_visibility=CiVisibility.PARTIAL,
        )
    )

    ids = rule_ids(result)
    assert "scope.very_large_file_count" in ids
    assert "scope.large_file_count" not in ids
    assert "scope.very_large_line_churn" in ids
    assert "scope.large_line_churn" not in ids
    assert "scope.large_individual_file_change" in ids
    assert "metadata.missing_description" in ids
    assert "metadata.draft_pull_request" in ids
    assert "metadata.large_commit_count" in ids
    assert "metadata.merge_conflict_observed" in ids
    assert ids == rule_ids(analyze_snapshot_signals(snapshot(files, body="   ", draft=True, commit_count=20, additions=3000, mergeable=False, ci_state=CiState.FAILING, ci_visibility=CiVisibility.PARTIAL)))
    assert result.signals[0].severity == SignalSeverity.HIGH


def test_classification_testing_dependency_and_rename_signals() -> None:
    files = [
        changed_file("backend/auth/permissions.py"),
        changed_file("frontend/src/api/client.js"),
        changed_file("migrations/001_drop_users.sql", patch=None),
        changed_file("package.json"),
        changed_file("package-lock.json"),
        changed_file("docs/login.md", status="renamed", previous_filename="tests/login_test.py"),
    ]
    result = analyze_snapshot_signals(snapshot(files, ci_state=CiState.MISSING))
    ids = rule_ids(result)

    assert "authentication.paths_changed" in ids
    assert "authorization.paths_changed" in ids
    assert "database.migration_changed" in ids
    assert "api.surface_changed" in ids
    assert "dependencies.manifest_changed" in ids
    assert "dependencies.lockfile_changed" in ids
    assert "dependencies.manifest_without_lockfile" not in ids
    assert "testing.sensitive_change_without_test_files" in ids
    assert "testing.production_change_without_test_files" not in ids
    assert "rename.file_moved_out_of_test_area" in ids
    assert "ci.missing" in ids


def test_dependency_missing_lockfile_and_lockfile_only_rules() -> None:
    missing_lock = analyze_snapshot_signals(snapshot([changed_file("package.json")]))
    assert "dependencies.manifest_without_lockfile" in rule_ids(missing_lock)

    pyproject = analyze_snapshot_signals(snapshot([changed_file("pyproject.toml")]))
    assert "dependencies.manifest_without_lockfile" not in rule_ids(pyproject)

    lockfile_only = analyze_snapshot_signals(snapshot([changed_file("yarn.lock")]))
    assert "dependencies.lockfile_only_change" in rule_ids(lockfile_only)

    lockfile_with_source = analyze_snapshot_signals(snapshot([changed_file("yarn.lock"), changed_file("backend/app/main.py")]))
    assert "dependencies.lockfile_only_change" not in rule_ids(lockfile_with_source)


def test_patch_parser_excludes_metadata_and_keeps_hunks_separate() -> None:
    parsed = parse_patch("@@ -1 +1 @@\n--- a/file.py\n+++ b/file.py\n-old\n+new\n context\n@@ -8 +8 @@\n+\n+unicodé")

    assert [line.kind for line in parsed.lines if line.content in {"new", "unicodé"}] == [
        PatchLineKind.ADDED,
        PatchLineKind.ADDED,
    ]
    assert all(line.content not in {"++ b/file.py", "-- a/file.py"} for line in parsed.lines)
    assert {line.hunk_index for line in parsed.lines if line.kind == PatchLineKind.ADDED} == {0, 1}


def test_patch_signal_detection_sanitizes_secret_like_literals() -> None:
    result = analyze_snapshot_signals(
        snapshot(
            [
                changed_file(
                    "backend/app/main.py",
                    patch=(
                        "@@ -1 +1 @@\n"
                        "+console.log('debug')\n"
                        "+# TODO follow up\n"
                        "+password = 'not-a-real-secret-fixture'\n"
                        "+verify=False\n"
                        "+try:\n"
                        "+    work()\n"
                        "+except Exception:\n"
                        "+    pass\n"
                    ),
                )
            ]
        )
    )
    ids = rule_ids(result)
    assert "code_quality.debug_statement_added" in ids
    assert "code_quality.todo_or_fixme_added" in ids
    assert "security.credential_like_literal_added" in ids
    assert "security.security_control_disabled_hint" in ids
    assert "code_quality.empty_exception_handler_added" in ids

    serialized = result.model_dump_json()
    assert "not-a-real-secret-fixture" not in serialized
    assert "password =" not in serialized
    credential_signal = next(signal for signal in result.signals if signal.rule_id == "security.credential_like_literal_added")
    assert credential_signal.evidence[0].observed_value == "password_like_literal"


def test_patch_false_positives_and_database_patch_rules() -> None:
    result = analyze_snapshot_signals(
        snapshot(
            [
                changed_file("docs/example.md", patch="@@ -1 +1 @@\n+console.log('example')\n+password = 'example'"),
                changed_file("tests/test_api.py", patch="@@ -1 +1 @@\n+pytest.mark.skip(reason='temporary')"),
                changed_file("migrations/002_change.sql", patch="@@ -1 +1 @@\n+ALTER TABLE users DROP COLUMN old_name"),
                changed_file("sql/report.sql", patch="@@ -1 +1 @@\n+DROP TABLE example"),
            ]
        )
    )
    ids = rule_ids(result)
    assert "code_quality.debug_statement_added" not in ids
    assert "security.credential_like_literal_added" not in ids
    assert "testing.test_skip_added" in ids
    assert "database.destructive_migration_hint" in ids
    migration_signal = next(signal for signal in result.signals if signal.rule_id == "database.destructive_migration_hint")
    assert migration_signal.affected_files == ["migrations/002_change.sql"]
    assert "ALTER TABLE" not in migration_signal.model_dump_json()


def test_completeness_generated_opaque_and_summary_counts() -> None:
    result = analyze_snapshot_signals(
        snapshot(
            [
                changed_file("dist/app.min.js", changes=600),
                changed_file("assets/logo.png", patch=None),
                changed_file("backend/app/main.py"),
            ],
            files_complete=False,
            commits_complete=False,
            ci_visibility=CiVisibility.UNAVAILABLE,
            ci_state=CiState.UNKNOWN,
        )
    )
    ids = rule_ids(result)
    assert "generated_content.generated_files_changed" in ids
    assert "generated_content.large_generated_change" in ids
    assert "completeness.opaque_files_changed" in ids
    assert "completeness.patch_coverage_incomplete" in ids
    assert "completeness.file_collection_incomplete" in ids
    assert "completeness.commit_collection_incomplete" in ids
    assert "ci.unavailable" in ids
    assert "ci.missing" not in ids
    assert result.summary.total_signals == len(result.signals)
    assert "assets/logo.png" in result.summary.files_with_signals
    assert result.summary.rules_version == "v1"


def test_no_negative_signals_for_test_and_documentation_only_changes() -> None:
    result = analyze_snapshot_signals(
        snapshot(
            [
                changed_file("tests/test_app.py"),
                changed_file("docs/readme.md"),
            ]
        )
    )
    ids = rule_ids(result)
    assert "testing.only_test_or_documentation_changes" in ids
    assert "testing.production_change_without_test_files" not in ids
    assert "testing.sensitive_change_without_test_files" not in ids


def test_evidence_ordering_uses_stable_case_tie_break() -> None:
    result = analyze_snapshot_signals(
        snapshot(
            [
                changed_file("backend/services/Auth.py", changes=600),
                changed_file("backend/services/auth.py", changes=600),
            ]
        )
    )

    signal = next(signal for signal in result.signals if signal.rule_id == "scope.large_individual_file_change")
    assert [evidence.file for evidence in signal.evidence] == [
        "backend/services/Auth.py",
        "backend/services/auth.py",
    ]
