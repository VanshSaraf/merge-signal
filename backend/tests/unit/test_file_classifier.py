from app.domain.file_classification import FileArea, FileKind, FileLanguage
from app.domain.pull_request import ChangedFile
from app.services.file_classifier import classify_changed_file, classify_changed_files, classify_path


def changed_file(
    filename: str,
    status: str = "modified",
    previous_filename: str | None = None,
    patch: str | None = "@@ -1 +1 @@",
) -> ChangedFile:
    return ChangedFile(
        filename=filename,
        status=status,
        additions=1,
        deletions=0,
        changes=1,
        patch=patch,
        previous_filename=previous_filename,
        blob_url=None,
    )


def assert_language(filename: str, language: FileLanguage) -> None:
    assert classify_path(filename).language == language


def assert_kind(filename: str, kind: FileKind) -> None:
    assert classify_path(filename).primary_kind == kind


def test_language_detection_supported_values() -> None:
    samples = {
        "app.py": FileLanguage.PYTHON,
        "app.JSX": FileLanguage.JAVASCRIPT,
        "app.mjs": FileLanguage.JAVASCRIPT,
        "app.tsx": FileLanguage.TYPESCRIPT,
        "App.java": FileLanguage.JAVA,
        "native.c": FileLanguage.C,
        "native.cpp": FileLanguage.CPP,
        "native.hpp": FileLanguage.CPP,
        "App.cs": FileLanguage.CSHARP,
        "main.go": FileLanguage.GO,
        "lib.rs": FileLanguage.RUST,
        "app.rb": FileLanguage.RUBY,
        "index.php": FileLanguage.PHP,
        "Main.kt": FileLanguage.KOTLIN,
        "App.swift": FileLanguage.SWIFT,
        "Job.scala": FileLanguage.SCALA,
        "query.SQL": FileLanguage.SQL,
        "script.sh": FileLanguage.SHELL,
        "script.zsh": FileLanguage.SHELL,
        "install.ps1": FileLanguage.POWERSHELL,
        "index.html": FileLanguage.HTML,
        "styles.css": FileLanguage.CSS,
        "styles.scss": FileLanguage.SCSS,
        "styles.less": FileLanguage.LESS,
        "package.json": FileLanguage.JSON,
        "workflow.yaml": FileLanguage.YAML,
        "pyproject.toml": FileLanguage.TOML,
        "pom.xml": FileLanguage.XML,
        "README.MDX": FileLanguage.MARKDOWN,
        "Dockerfile": FileLanguage.DOCKERFILE,
        "main.tfvars": FileLanguage.TERRAFORM,
        "service.proto": FileLanguage.PROTOBUF,
        "schema.graphql": FileLanguage.GRAPHQL,
        "schema.gql": FileLanguage.GRAPHQL,
        "archive.unknown": FileLanguage.UNKNOWN,
        ".gitignore": FileLanguage.UNKNOWN,
        "LICENSE": FileLanguage.UNKNOWN,
    }

    for filename, language in samples.items():
        assert_language(filename, language)


def test_primary_file_kind_rules_and_precedence() -> None:
    samples = {
        "src/auth/login.py": FileKind.SOURCE,
        "tests/auth/test_login.py": FileKind.TEST,
        "frontend/src/App.test.jsx": FileKind.TEST,
        "UserServiceTest.java": FileKind.TEST,
        "user_test.go": FileKind.TEST,
        "README.md": FileKind.DOCUMENTATION,
        "package.json": FileKind.DEPENDENCY_MANIFEST,
        "package-lock.json": FileKind.DEPENDENCY_LOCKFILE,
        "migrations/004_add_users.sql": FileKind.DATABASE_MIGRATION,
        "V12__create_users.sql": FileKind.DATABASE_MIGRATION,
        ".github/workflows/test.yml": FileKind.CI_CONFIGURATION,
        "Dockerfile": FileKind.INFRASTRUCTURE,
        "infra/main.tf": FileKind.INFRASTRUCTURE,
        "k8s/deployment.yaml": FileKind.INFRASTRUCTURE,
        ".env.example": FileKind.CONFIGURATION,
        "dist/app.min.js": FileKind.GENERATED,
        "assets/logo.png": FileKind.ASSET,
        "build/output.jar": FileKind.GENERATED,
        "download.zip": FileKind.BINARY,
        "unknownfile.weird": FileKind.UNKNOWN,
        "tests/migrations/test_user_migration.py": FileKind.DATABASE_MIGRATION,
        "tests/fixtures/package-lock.json": FileKind.DEPENDENCY_LOCKFILE,
        ".github/workflows/README.md": FileKind.CI_CONFIGURATION,
        "docs/examples/Dockerfile": FileKind.DOCUMENTATION,
        "build.gradle": FileKind.DEPENDENCY_MANIFEST,
        "generator/service.py": FileKind.SOURCE,
    }

    for filename, kind in samples.items():
        assert_kind(filename, kind)


def test_functional_areas_and_false_positive_avoidance() -> None:
    classification = classify_path("backend/auth/permissions.py")
    assert classification.areas == [
        FileArea.AUTHENTICATION,
        FileArea.AUTHORIZATION,
        FileArea.BACKEND,
        FileArea.SECURITY,
    ]

    assert classify_path("frontend/src/api/client.js").areas == [FileArea.API, FileArea.FRONTEND]
    assert classify_path(".github/workflows/deploy.yml").areas == [FileArea.CI_CD, FileArea.INFRASTRUCTURE]
    assert classify_path("package.json").areas == [FileArea.BUILD_TOOLING, FileArea.DEPENDENCIES]
    assert classify_path("tests/api/test_users.py").areas == [FileArea.API, FileArea.TESTING]
    assert classify_path("sql/report.sql").areas == [FileArea.DATABASE]

    false_positive_paths = [
        "author/profile.py",
        "roleplay/game.js",
        "debug/logger.py",
        "contest/result.js",
        "latest/report.py",
        "app/main.py",
        "scripts/plain.js",
        "scripts/plain.py",
    ]
    for path in false_positive_paths:
        areas = classify_path(path).areas
        assert FileArea.AUTHENTICATION not in areas
        assert FileArea.AUTHORIZATION not in areas
        assert FileArea.DATABASE not in areas
        assert FileArea.TESTING not in areas
        assert FileArea.FRONTEND not in areas
        assert FileArea.BACKEND not in areas


def test_path_safety_warnings_do_not_crash() -> None:
    paths = [
        "docs/My File.md",
        "unicodé/文件.py",
        "src\\app.py",
        "src//app.py",
        "/src/app.py",
        "src/./app.py",
        "src/../app.py",
        "src/\x00/app.py",
        "src/\x1f/app.py",
        "src/" + "a" * 4100 + ".py",
        "percent%file.py",
    ]

    for path in paths:
        classification = classify_path(path)
        assert classification.primary_kind in FileKind
        if any(marker in path for marker in ["\\", "//", "\x00", "\x1f"]) or path.startswith("/") or "/./" in path or "/../" in path or len(path) > 4096:
            assert classification.warnings


def test_renamed_file_classifies_current_and_previous_paths_independently() -> None:
    file = classify_changed_file(
        changed_file(
            "backend/auth/login.py",
            status="renamed",
            previous_filename="docs/login.md",
        )
    )

    assert file.classification.primary_kind == FileKind.SOURCE
    assert FileArea.AUTHENTICATION in file.classification.areas
    assert file.previous_classification is not None
    assert file.previous_classification.primary_kind == FileKind.DOCUMENTATION


def test_nextjs_admin_dynamic_protected_route_context_and_domains() -> None:
    classification = classify_path("app/(protected)/admin/cohort/[id]/page.tsx")

    assert classification.primary_kind == FileKind.SOURCE
    assert classification.language == FileLanguage.TYPESCRIPT
    assert FileArea.FRONTEND in classification.areas
    assert classification.context.framework == "nextjs_app_router"
    assert classification.context.component_role == "route_page"
    assert "admin" in classification.context.areas
    assert "protected_route_group" in classification.context.access_context
    assert "dynamic_route" in classification.context.route_context
    assert classification.context.is_dynamic_route is True
    assert classification.context.is_user_facing is True
    assert classification.context.domains == ["cohort"]
    assert "(protected)" not in classification.context.domains
    assert "[id]" not in classification.context.domains


def test_common_context_roles_are_path_based_and_unknown_stays_bounded() -> None:
    assert classify_path("app/api/users/route.ts").context.component_role == "route_handler"
    assert classify_path("app/dashboard/layout.tsx").context.component_role == "route_layout"
    assert classify_path("frontend/src/components/UserCard.tsx").context.component_role == "frontend_component"
    assert classify_path("backend/services/payments.py").context.component_role == "backend_service"
    assert classify_path(".github/workflows/test.yml").context.is_configuration is True
    assert classify_path("docs/architecture.md").context.is_documentation is True
    assert classify_path("migrations/001_create_users.sql").context.is_database_change is True
    assert classify_path("unknown.thing").context.classification_confidence == "low"


def test_summary_counts_are_deterministic_and_consistent() -> None:
    files, summary = classify_changed_files(
        [
            changed_file("backend/auth/login.py"),
            changed_file("tests/api/test_login.py"),
            changed_file("package-lock.json"),
            changed_file("assets/logo.png", patch=None),
            changed_file("unknown.weird", status="renamed", previous_filename="docs/old.md"),
        ]
    )

    kind_total = sum(item.count for item in summary.counts_by_kind)
    language_total = sum(item.count for item in summary.counts_by_language)
    area_total = sum(item.count for item in summary.counts_by_area)

    assert summary.total_files == len(files)
    assert kind_total == summary.total_files
    assert language_total == summary.total_files
    assert area_total >= summary.total_files - summary.unknown_files
    assert summary.renamed_files == 1
    assert summary.files_with_previous_classification == 1
    assert summary.files_without_patch == 1
    assert summary.unknown_files == 1
    assert summary.warnings == sorted(set(summary.warnings))


def test_empty_summary() -> None:
    files, summary = classify_changed_files([])

    assert files == []
    assert summary.total_files == 0
    assert summary.classified_files == 0
    assert summary.unknown_files == 0
    assert summary.counts_by_kind == []
    assert summary.counts_by_area == []
    assert summary.counts_by_language == []
