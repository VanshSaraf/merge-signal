from dataclasses import dataclass
from re import Pattern, compile

from app.domain.file_classification import FileArea, FileKind, FileLanguage


@dataclass(frozen=True)
class Rule:
    rule_id: str
    match_type: str
    value: str
    description: str
    kind: FileKind | None = None
    areas: tuple[FileArea, ...] = ()
    language: FileLanguage | None = None
    exact_filenames: frozenset[str] = frozenset()
    path_segments: frozenset[str] = frozenset()
    path_prefixes: tuple[str, ...] = ()
    extensions: frozenset[str] = frozenset()
    filename_patterns: tuple[Pattern[str], ...] = ()


PRIMARY_KIND_PRECEDENCE: tuple[FileKind, ...] = (
    FileKind.DEPENDENCY_LOCKFILE,
    FileKind.DEPENDENCY_MANIFEST,
    FileKind.DATABASE_MIGRATION,
    FileKind.CI_CONFIGURATION,
    FileKind.TEST,
    FileKind.DOCUMENTATION,
    FileKind.INFRASTRUCTURE,
    FileKind.CONFIGURATION,
    FileKind.GENERATED,
    FileKind.BINARY,
    FileKind.ASSET,
    FileKind.SOURCE,
    FileKind.UNKNOWN,
)

SOURCE_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".mts",
        ".cts",
        ".java",
        ".c",
        ".cc",
        ".cpp",
        ".cxx",
        ".hpp",
        ".hh",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".kt",
        ".kts",
        ".swift",
        ".scala",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".html",
        ".css",
        ".scss",
        ".less",
        ".proto",
        ".graphql",
        ".gql",
    }
)

LANGUAGE_BY_EXTENSION = {
    ".py": FileLanguage.PYTHON,
    ".js": FileLanguage.JAVASCRIPT,
    ".jsx": FileLanguage.JAVASCRIPT,
    ".mjs": FileLanguage.JAVASCRIPT,
    ".cjs": FileLanguage.JAVASCRIPT,
    ".ts": FileLanguage.TYPESCRIPT,
    ".tsx": FileLanguage.TYPESCRIPT,
    ".mts": FileLanguage.TYPESCRIPT,
    ".cts": FileLanguage.TYPESCRIPT,
    ".java": FileLanguage.JAVA,
    ".c": FileLanguage.C,
    ".cc": FileLanguage.CPP,
    ".cpp": FileLanguage.CPP,
    ".cxx": FileLanguage.CPP,
    ".hpp": FileLanguage.CPP,
    ".hh": FileLanguage.CPP,
    ".cs": FileLanguage.CSHARP,
    ".go": FileLanguage.GO,
    ".rs": FileLanguage.RUST,
    ".rb": FileLanguage.RUBY,
    ".php": FileLanguage.PHP,
    ".kt": FileLanguage.KOTLIN,
    ".kts": FileLanguage.KOTLIN,
    ".swift": FileLanguage.SWIFT,
    ".scala": FileLanguage.SCALA,
    ".sql": FileLanguage.SQL,
    ".sh": FileLanguage.SHELL,
    ".bash": FileLanguage.SHELL,
    ".zsh": FileLanguage.SHELL,
    ".ps1": FileLanguage.POWERSHELL,
    ".html": FileLanguage.HTML,
    ".css": FileLanguage.CSS,
    ".scss": FileLanguage.SCSS,
    ".less": FileLanguage.LESS,
    ".json": FileLanguage.JSON,
    ".yml": FileLanguage.YAML,
    ".yaml": FileLanguage.YAML,
    ".toml": FileLanguage.TOML,
    ".xml": FileLanguage.XML,
    ".md": FileLanguage.MARKDOWN,
    ".mdx": FileLanguage.MARKDOWN,
    ".tf": FileLanguage.TERRAFORM,
    ".tfvars": FileLanguage.TERRAFORM,
    ".proto": FileLanguage.PROTOBUF,
    ".graphql": FileLanguage.GRAPHQL,
    ".gql": FileLanguage.GRAPHQL,
}

LANGUAGE_EXACT_FILENAMES = {
    "dockerfile": FileLanguage.DOCKERFILE,
}

DEPENDENCY_MANIFESTS = frozenset(
    {
        "package.json",
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "pipfile",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
        "go.mod",
        "cargo.toml",
        "gemfile",
        "composer.json",
        "packages.config",
        "directory.packages.props",
    }
)
DEPENDENCY_LOCKFILES = frozenset(
    {
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "pipfile.lock",
        "uv.lock",
        "go.sum",
        "cargo.lock",
        "gemfile.lock",
        "composer.lock",
        "gradle.lockfile",
    }
)

RULES: tuple[Rule, ...] = (
    Rule("kind.dependency.lockfile", "exact_filename", "lockfile", "Dependency lockfile.", kind=FileKind.DEPENDENCY_LOCKFILE, areas=(FileArea.DEPENDENCIES,), exact_filenames=DEPENDENCY_LOCKFILES),
    Rule("kind.dependency.manifest", "exact_filename", "manifest", "Dependency manifest.", kind=FileKind.DEPENDENCY_MANIFEST, areas=(FileArea.DEPENDENCIES, FileArea.BUILD_TOOLING), exact_filenames=DEPENDENCY_MANIFESTS),
    Rule("kind.dependency.requirements_pattern", "filename_pattern", "requirements-*.txt", "Python dependency manifest.", kind=FileKind.DEPENDENCY_MANIFEST, areas=(FileArea.DEPENDENCIES,), filename_patterns=(compile(r"^requirements-[a-z0-9_.-]+\.txt$"),)),
    Rule("kind.migration.path", "path_prefix", "migrations", "File is in a controlled migration path.", kind=FileKind.DATABASE_MIGRATION, areas=(FileArea.DATABASE,), path_segments=frozenset({"migrations", "migration"}), path_prefixes=("migrations/", "migration/", "db/migrate/", "database/migrations/", "prisma/migrations/", "alembic/versions/")),
    Rule("kind.migration.pattern", "filename_pattern", "migration filename", "File matches a database migration naming pattern.", kind=FileKind.DATABASE_MIGRATION, areas=(FileArea.DATABASE,), filename_patterns=(compile(r"^(v\d+__.+|[0-9]{3,}_.+)\.(sql|py)$"),)),
    Rule("kind.ci.github_workflows", "path_prefix", ".github/workflows/", "GitHub Actions workflow configuration.", kind=FileKind.CI_CONFIGURATION, areas=(FileArea.CI_CD, FileArea.INFRASTRUCTURE), path_prefixes=(".github/workflows/",)),
    Rule("kind.ci.common_files", "exact_filename", "ci config", "Known CI/CD configuration file.", kind=FileKind.CI_CONFIGURATION, areas=(FileArea.CI_CD,), exact_filenames=frozenset({".gitlab-ci.yml", "jenkinsfile", "azure-pipelines.yml", "bitbucket-pipelines.yml", ".travis.yml", ".drone.yml"})),
    Rule("kind.ci.circleci", "path_prefix", ".circleci/", "CircleCI configuration.", kind=FileKind.CI_CONFIGURATION, areas=(FileArea.CI_CD,), path_prefixes=(".circleci/",)),
    Rule("kind.test.segment", "path_segment", "tests", "Path contains an exact test-related segment.", kind=FileKind.TEST, areas=(FileArea.TESTING,), path_segments=frozenset({"test", "tests", "__tests__", "spec", "specs"})),
    Rule("kind.test.filename", "filename_pattern", "test filename", "Filename matches a controlled test pattern.", kind=FileKind.TEST, areas=(FileArea.TESTING,), filename_patterns=(compile(r"^test_.+\.py$"), compile(r"^.+_test\.py$"), compile(r"^.+\.(test|spec)\.(js|jsx|ts|tsx)$"), compile(r"^.+test\.java$"), compile(r"^.+_(test|spec)\.(go|rb)$"))),
    Rule("kind.documentation.filename", "exact_filename", "documentation filename", "Known documentation file.", kind=FileKind.DOCUMENTATION, areas=(FileArea.DOCUMENTATION,), exact_filenames=frozenset({"readme", "readme.md", "readme.mdx", "contributing", "contributing.md", "changelog", "changelog.md", "security.md", "code_of_conduct", "code_of_conduct.md", "license", "license.md"})),
    Rule("kind.documentation.path", "path_segment", "docs", "Path contains a documentation segment.", kind=FileKind.DOCUMENTATION, areas=(FileArea.DOCUMENTATION,), path_segments=frozenset({"docs", "documentation"})),
    Rule("kind.documentation.markdown", "extension", ".md", "Markdown documentation.", kind=FileKind.DOCUMENTATION, areas=(FileArea.DOCUMENTATION,), extensions=frozenset({".md", ".mdx"})),
    Rule("kind.infrastructure.dockerfile", "exact_filename", "Dockerfile", "Docker build file.", kind=FileKind.INFRASTRUCTURE, areas=(FileArea.INFRASTRUCTURE, FileArea.BUILD_TOOLING), filename_patterns=(compile(r"^dockerfile([._-].+)?$"),)),
    Rule("kind.infrastructure.terraform", "extension", ".tf", "Terraform infrastructure file.", kind=FileKind.INFRASTRUCTURE, areas=(FileArea.INFRASTRUCTURE,), extensions=frozenset({".tf", ".tfvars"})),
    Rule("kind.infrastructure.path", "path_segment", "infra", "Infrastructure path segment.", kind=FileKind.INFRASTRUCTURE, areas=(FileArea.INFRASTRUCTURE,), path_segments=frozenset({"infrastructure", "infra", "terraform", "kubernetes", "k8s", "helm", "ansible"})),
    Rule("kind.infrastructure.compose", "exact_filename", "compose", "Container compose configuration.", kind=FileKind.INFRASTRUCTURE, areas=(FileArea.INFRASTRUCTURE,), exact_filenames=frozenset({"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml", "chart.yaml"})),
    Rule("kind.configuration.path", "path_segment", "config", "Configuration path segment.", kind=FileKind.CONFIGURATION, areas=(FileArea.CONFIGURATION,), path_segments=frozenset({"config", "configuration"})),
    Rule("kind.configuration.files", "exact_filename", "configuration filename", "Known configuration file.", kind=FileKind.CONFIGURATION, areas=(FileArea.CONFIGURATION,), exact_filenames=frozenset({".env.example", ".editorconfig", ".nvmrc", ".python-version", "application.yml", "application.yaml", "application.properties"})),
    Rule("kind.configuration.pattern", "filename_pattern", "configuration pattern", "Known configuration filename pattern.", kind=FileKind.CONFIGURATION, areas=(FileArea.CONFIGURATION, FileArea.BUILD_TOOLING), filename_patterns=(compile(r"^\.env\..+\.example$"), compile(r"^(tsconfig|jsconfig).+\.json$"), compile(r"^(.+)?(eslint|prettier|babel|vite|webpack|rollup)\.config\.(js|mjs|cjs|ts)$"))),
    Rule("kind.generated.path", "path_segment", "generated", "Generated or vendor path segment.", kind=FileKind.GENERATED, areas=(FileArea.GENERATED,), path_segments=frozenset({"generated", "gen", "dist", "build", "coverage", "vendor", "node_modules", "target"})),
    Rule("kind.generated.pattern", "filename_pattern", "generated filename", "Generated filename pattern.", kind=FileKind.GENERATED, areas=(FileArea.GENERATED,), filename_patterns=(compile(r"^.+\.min\.(js|css)$"), compile(r"^.+\.map$"), compile(r"^.+\.pb\.(go|py|rb|cc|h)$"))),
    Rule("kind.binary.extension", "extension", "binary extension", "Compiled, archive, or opaque binary artifact.", kind=FileKind.BINARY, extensions=frozenset({".zip", ".tar", ".gz", ".7z", ".rar", ".jar", ".war", ".exe", ".dll", ".so", ".dylib", ".class", ".pyc", ".woff", ".woff2", ".ttf", ".otf"})),
    Rule("kind.asset.extension", "extension", "asset extension", "User-facing media or design asset.", kind=FileKind.ASSET, extensions=frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".mp3", ".wav", ".mp4", ".webm", ".pdf"})),
    Rule("kind.source.extension", "extension", "source extension", "Recognized source-code extension.", kind=FileKind.SOURCE, extensions=SOURCE_EXTENSIONS),
    Rule("area.frontend.segment", "path_segment", "frontend", "Frontend path segment.", areas=(FileArea.FRONTEND,), path_segments=frozenset({"frontend", "client", "web", "ui", "public"})),
    Rule("area.frontend.prefix", "path_prefix", "src/components", "Frontend UI path prefix.", areas=(FileArea.FRONTEND,), path_prefixes=("src/components/", "src/pages/", "src/views/", "src/hooks/")),
    Rule("area.backend.segment", "path_segment", "backend", "Backend path segment.", areas=(FileArea.BACKEND,), path_segments=frozenset({"backend", "server", "services", "workers", "jobs"})),
    Rule("area.backend.prefix", "path_prefix", "src/server", "Backend server path prefix.", areas=(FileArea.BACKEND,), path_prefixes=("src/server/", "app/services/")),
    Rule("area.api.segment", "path_segment", "api", "API path segment.", areas=(FileArea.API,), path_segments=frozenset({"api", "routes", "routers", "controllers", "endpoints", "openapi", "swagger"})),
    Rule("area.authentication.segment", "path_segment", "auth", "Authentication-related path segment.", areas=(FileArea.AUTHENTICATION, FileArea.SECURITY), path_segments=frozenset({"auth", "authentication", "login", "oauth", "jwt", "session", "sessions"})),
    Rule("area.authorization.segment", "path_segment", "permissions", "Authorization-related path segment.", areas=(FileArea.AUTHORIZATION, FileArea.SECURITY), path_segments=frozenset({"authorization", "permissions", "permission", "roles", "role", "access_control", "access-control", "rbac", "acl"}), filename_patterns=(compile(r"^(permission|permissions|role|roles|rbac|acl)\.(py|js|jsx|ts|tsx|go|rb|java|cs)$"),)),
    Rule("area.security.segment", "path_segment", "security", "Security-related path segment.", areas=(FileArea.SECURITY,), path_segments=frozenset({"security", "crypto", "encryption", "secrets", "vulnerability"})),
    Rule("area.database.segment", "path_segment", "database", "Database-related path segment.", areas=(FileArea.DATABASE,), path_segments=frozenset({"database", "databases", "db", "migrations", "schema", "prisma", "alembic"})),
)
