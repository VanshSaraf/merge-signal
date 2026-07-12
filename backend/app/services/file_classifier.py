from collections import Counter
from dataclasses import dataclass

from app.domain.file_classification import (
    ClassificationCount,
    ClassificationMatch,
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

    return FileClassification(
        primary_kind=primary_kind,
        areas=sorted(areas, key=lambda area: area.value),
        language=language,
        matches=sorted(matches.values(), key=lambda match: (match.rule_id, match.match_type, match.value)),
        warnings=_unique_sorted(warnings),
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
