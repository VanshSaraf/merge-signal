from collections import Counter
from dataclasses import dataclass

from app.domain.file_classification import (
    ClassificationCount,
    ClassificationMatch,
    FileContext,
    FileArea,
    FileClassification,
    FileClassificationSummary,
    FileKind,
    FileLanguage,
)
from app.domain.pull_request import ChangedFile
from app.services.file_classification_rules import (
    LANGUAGE_BY_EXTENSION,
    LANGUAGE_EXACT_FILENAMES,
    PRIMARY_KIND_PRECEDENCE,
    RULES,
    Rule,
)


@dataclass(frozen=True)
class PathInfo:
    original: str
    normalized: str
    segments: tuple[str, ...]
    filename: str
    extension: str
    warnings: tuple[str, ...]


def classify_path(filename: str) -> FileClassification:
    """Classify a repository-relative path string without filesystem access."""
    info = _path_info(filename)
    matches: dict[tuple[str, str, str], ClassificationMatch] = {}
    matched_kinds: set[FileKind] = set()
    areas: set[FileArea] = set()

    for rule in RULES:
        if _rule_matches(rule, info):
            matches[(rule.rule_id, rule.match_type, rule.value)] = ClassificationMatch(
                rule_id=rule.rule_id,
                match_type=rule.match_type,
                value=rule.value,
                description=rule.description,
            )
            if rule.kind:
                matched_kinds.add(rule.kind)
            areas.update(rule.areas)

    language, language_match = _detect_language(info)
    if language_match:
        matches[(language_match.rule_id, language_match.match_type, language_match.value)] = language_match

    primary_kind = _resolve_primary_kind(matched_kinds)
    warnings = list(info.warnings)
    if language == FileLanguage.SQL:
        areas.add(FileArea.DATABASE)
    if primary_kind == FileKind.UNKNOWN:
        warnings.append("No explicit file-kind rule matched.")
    if language == FileLanguage.UNKNOWN:
        warnings.append("No explicit language rule matched.")
    context = _build_file_context(info, primary_kind, sorted(areas, key=lambda area: area.value), language)
    if "frontend" in context.areas:
        areas.add(FileArea.FRONTEND)
    if "api" in context.areas:
        areas.add(FileArea.API)
    if context.is_database_change:
        areas.add(FileArea.DATABASE)

    return FileClassification(
        primary_kind=primary_kind,
        areas=sorted(areas, key=lambda area: area.value),
        language=language,
        context=context,
        matches=sorted(matches.values(), key=lambda match: (match.rule_id, match.match_type, match.value)),
        warnings=_unique_sorted([*warnings, *context.warnings]),
    )


def classify_changed_file(file: ChangedFile) -> ChangedFile:
    classification = classify_path(file.filename)
    previous_classification = classify_path(file.previous_filename) if file.previous_filename else None
    return file.model_copy(
        update={
            "classification": classification,
            "previous_classification": previous_classification,
        }
    )


def classify_changed_files(files: list[ChangedFile]) -> tuple[list[ChangedFile], FileClassificationSummary]:
    classified = [classify_changed_file(file) for file in files]
    return classified, summarize_classifications(classified)


def summarize_classifications(files: list[ChangedFile]) -> FileClassificationSummary:
    kind_counts = Counter(file.classification.primary_kind for file in files)
    area_counts: Counter[FileArea] = Counter()
    language_counts = Counter(file.classification.language for file in files)
    warnings: list[str] = []

    for file in files:
        area_counts.update(file.classification.areas)
        warnings.extend(file.classification.warnings)
        if file.previous_classification:
            warnings.extend(file.previous_classification.warnings)

    unknown_files = kind_counts[FileKind.UNKNOWN]
    return FileClassificationSummary(
        total_files=len(files),
        classified_files=len(files) - unknown_files,
        unknown_files=unknown_files,
        counts_by_kind=_counts_for(FileKind, kind_counts),
        counts_by_area=_counts_for(FileArea, area_counts),
        counts_by_language=_counts_for(FileLanguage, language_counts),
        renamed_files=sum(1 for file in files if file.status == "renamed" or file.previous_filename),
        files_with_previous_classification=sum(1 for file in files if file.previous_classification is not None),
        files_without_patch=sum(1 for file in files if file.patch is None),
        warnings=_unique_sorted(warnings),
    )


def _path_info(path: str) -> PathInfo:
    warnings: list[str] = []
    if len(path) > 4096:
        warnings.append("Path is unusually long.")
    if "\\" in path:
        warnings.append("Path contains a literal backslash.")
    if path.startswith("/"):
        warnings.append("Path starts with a slash; GitHub paths should be repository-relative.")
    if "//" in path:
        warnings.append("Path contains repeated separators.")
    if any(ord(character) < 32 for character in path):
        warnings.append("Path contains a control character.")

    normalized = path.casefold()
    raw_segments = tuple(normalized.split("/")) if normalized else ()
    if any(segment in {".", ".."} for segment in raw_segments):
        warnings.append("Path contains dot navigation segments.")
    segments = tuple(segment for segment in raw_segments if segment)
    filename = segments[-1] if segments else normalized
    extension = _extension(filename)
    return PathInfo(
        original=path,
        normalized=normalized,
        segments=segments,
        filename=filename,
        extension=extension,
        warnings=tuple(_unique_sorted(warnings)),
    )


def _extension(filename: str) -> str:
    if filename.startswith(".") and filename.count(".") == 1:
        return ""
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[1]


def _rule_matches(rule: Rule, info: PathInfo) -> bool:
    return (
        info.filename in rule.exact_filenames
        or any(segment in rule.path_segments for segment in info.segments)
        or any(info.normalized.startswith(prefix) for prefix in rule.path_prefixes)
        or info.extension in rule.extensions
        or any(pattern.match(info.filename) for pattern in rule.filename_patterns)
    )


def _detect_language(info: PathInfo) -> tuple[FileLanguage, ClassificationMatch | None]:
    if info.filename in LANGUAGE_EXACT_FILENAMES:
        return (
            LANGUAGE_EXACT_FILENAMES[info.filename],
            ClassificationMatch(
                rule_id="language.exact_filename",
                match_type="exact_filename",
                value=info.filename,
                description="Language detected from exact filename.",
            ),
        )
    if info.extension in LANGUAGE_BY_EXTENSION:
        return (
            LANGUAGE_BY_EXTENSION[info.extension],
            ClassificationMatch(
                rule_id="language.extension",
                match_type="extension",
                value=info.extension,
                description="Language detected from file extension.",
            ),
        )
    if info.filename.startswith("dockerfile"):
        return (
            FileLanguage.DOCKERFILE,
            ClassificationMatch(
                rule_id="language.dockerfile_pattern",
                match_type="filename_pattern",
                value="Dockerfile",
                description="Language detected from Dockerfile naming pattern.",
            ),
        )
    return FileLanguage.UNKNOWN, None


def _resolve_primary_kind(matched_kinds: set[FileKind]) -> FileKind:
    for kind in PRIMARY_KIND_PRECEDENCE:
        if kind in matched_kinds:
            return kind
    return FileKind.UNKNOWN


def _counts_for(enum_type, counts: Counter) -> list[ClassificationCount]:
    return [
        ClassificationCount(name=item.value, count=counts[item])
        for item in enum_type
        if counts[item] > 0
    ]


def _unique_sorted(values: list[str] | tuple[str, ...]) -> list[str]:
    return sorted(set(values))


NEXT_ROUTE_FILENAMES = {
    "page": "route_page",
    "layout": "route_layout",
    "route": "route_handler",
    "loading": "loading_boundary",
    "error": "error_boundary",
    "not-found": "not_found_boundary",
}

RESERVED_DOMAIN_SEGMENTS = {
    "src",
    "app",
    "pages",
    "components",
    "component",
    "lib",
    "libs",
    "utils",
    "util",
    "services",
    "service",
    "api",
    "tests",
    "test",
    "__tests__",
    "fixtures",
    "fixture",
    "hooks",
    "styles",
    "public",
    "server",
    "client",
    "backend",
    "frontend",
    "admin",
    "auth",
    "database",
    "db",
}

GENERIC_FILENAMES = {
    "index",
    "main",
    "page",
    "layout",
    "route",
    "loading",
    "error",
    "not-found",
}


def _build_file_context(info: PathInfo, kind: FileKind, areas: list[FileArea], language: FileLanguage) -> FileContext:
    evidence: list[ClassificationMatch] = []
    context_areas = {area.value for area in areas}
    route_context: set[str] = set()
    access_context: set[str] = set()
    domains = _extract_domains(info)
    stem = info.filename.rsplit(".", 1)[0] if "." in info.filename else info.filename
    framework = None
    component_role = None
    is_dynamic_route = any(_is_dynamic_segment(segment) for segment in info.segments)
    is_next_app_path = bool(info.segments and info.segments[0] == "app" and stem in NEXT_ROUTE_FILENAMES)

    if is_next_app_path:
        framework = "nextjs_app_router"
        component_role = NEXT_ROUTE_FILENAMES[stem]
        route_context.add("application_route")
        context_areas.add("frontend")
        evidence.append(_context_match("context.nextjs_app_router", "path_prefix", "app/", "Next.js App Router path convention."))
        evidence.append(_context_match(f"context.nextjs.{component_role}", "filename", info.filename, f"Next.js {component_role.replace('_', ' ')} file."))
    elif any(segment in {"components", "component"} for segment in info.segments) and language in {FileLanguage.JAVASCRIPT, FileLanguage.TYPESCRIPT}:
        component_role = "frontend_component"
        context_areas.add("frontend")
        evidence.append(_context_match("context.frontend_component", "path_segment", "components", "Frontend component path convention."))
    elif any(segment in {"controllers", "controller", "routes", "routers"} for segment in info.segments):
        component_role = "backend_controller"
        context_areas.add("backend")
        context_areas.add("api")
        evidence.append(_context_match("context.backend_controller", "path_segment", "routes", "Backend route/controller path convention."))
    elif any(segment in {"services", "service"} for segment in info.segments):
        component_role = "backend_service"
        context_areas.add("backend")
        evidence.append(_context_match("context.backend_service", "path_segment", "services", "Backend service path convention."))

    for segment in info.segments:
        if segment.startswith("(") and segment.endswith(")"):
            label = segment[1:-1]
            route_context.add(f"route_group:{label}")
            evidence.append(_context_match("context.route_group", "path_segment", segment, "Next.js route group segment."))
            if label in {"protected", "private", "authenticated", "auth"}:
                access_context.add("protected_route_group")
                evidence.append(_context_match("context.access.protected_route_group", "path_segment", segment, "Observable protected route group name."))
        if _is_dynamic_segment(segment):
            route_context.add("dynamic_route")
            evidence.append(_context_match("context.dynamic_route", "path_segment", segment, "Dynamic route parameter segment."))
        if segment == "admin":
            context_areas.add("admin")
            evidence.append(_context_match("context.area.admin", "path_segment", "admin", "Admin path segment."))
        if segment == "api":
            context_areas.add("api")

    is_user_facing = bool(framework == "nextjs_app_router" and component_role in {"route_page", "route_layout", "loading_boundary", "error_boundary", "not_found_boundary"})
    confidence = "high" if evidence else ("medium" if kind != FileKind.UNKNOWN or language != FileLanguage.UNKNOWN else "low")
    return FileContext(
        framework=framework,
        component_role=component_role,
        route_context=_unique_sorted(tuple(route_context)),
        access_context=_unique_sorted(tuple(access_context)),
        domains=domains,
        areas=_unique_sorted(tuple(context_areas)),
        is_user_facing=is_user_facing,
        is_dynamic_route=is_dynamic_route,
        is_test=kind == FileKind.TEST,
        is_generated=kind in {FileKind.GENERATED, FileKind.BINARY},
        is_configuration=kind in {FileKind.CONFIGURATION, FileKind.CI_CONFIGURATION, FileKind.DEPENDENCY_MANIFEST, FileKind.DEPENDENCY_LOCKFILE},
        is_documentation=kind == FileKind.DOCUMENTATION,
        is_database_change=kind == FileKind.DATABASE_MIGRATION or FileArea.DATABASE in areas,
        classification_confidence=confidence,
        evidence=sorted(evidence, key=lambda match: (match.rule_id, match.match_type, match.value)),
        warnings=[],
    )


def _extract_domains(info: PathInfo) -> list[str]:
    domains: list[str] = []
    for segment in info.segments[:-1]:
        if (
            not segment
            or segment in RESERVED_DOMAIN_SEGMENTS
            or segment.startswith("(")
            or _is_dynamic_segment(segment)
            or "." in segment
        ):
            continue
        cleaned = "".join(character for character in segment if character.isalnum() or character in {"-", "_"}).strip("-_")
        if cleaned and cleaned not in RESERVED_DOMAIN_SEGMENTS and cleaned not in domains:
            domains.append(cleaned)
        if len(domains) >= 4:
            break
    stem = info.filename.rsplit(".", 1)[0] if "." in info.filename else info.filename
    if stem not in GENERIC_FILENAMES and stem not in RESERVED_DOMAIN_SEGMENTS and not _is_dynamic_segment(stem):
        cleaned_stem = "".join(character for character in stem if character.isalnum() or character in {"-", "_"}).strip("-_")
        if cleaned_stem and cleaned_stem not in domains:
            domains.append(cleaned_stem)
    return domains[:4]


def _is_dynamic_segment(segment: str) -> bool:
    return segment.startswith("[") and segment.endswith("]")


def _context_match(rule_id: str, match_type: str, value: str, description: str) -> ClassificationMatch:
    return ClassificationMatch(rule_id=rule_id, match_type=match_type, value=value, description=description)
