from collections import defaultdict

from app.domain.file_classification import FileKind
from app.domain.file_priority import FilePriorityFactor, FilePriorityLevel, FilePrioritySummary, RankedFile
from app.domain.pull_request import ChangedFile, PullRequestSnapshot
from app.domain.review_signal import ReviewSignal
from app.file_priority.ordering import LEVEL_ORDER, unique_sorted
from app.file_priority.rules import (
    FACTOR_GROUP_CAPS,
    FACTOR_GROUP_ORDER,
    MAX_FILE_PRIORITY_SCORE,
    RENAME_SENSITIVE_AREAS,
    SENSITIVE_AREA_WEIGHTS,
    SENSITIVE_KIND_WEIGHTS,
    SIGNAL_PRIORITY_WEIGHT_BY_RULE_ID,
)
from app.file_priority.summary import summarize_file_priorities

FILE_LIMITATIONS = [
    "Review priority is a deterministic review-ordering heuristic, not a probability or defect score.",
    "Ranking does not replace human review.",
]

PATCH_INELIGIBLE_ASSET_KINDS = frozenset({FileKind.ASSET})
OPAQUE_VISIBILITY_KINDS = frozenset({FileKind.BINARY, FileKind.GENERATED})


def level_for_file_priority(score: int) -> FilePriorityLevel:
    if score < 0 or score > MAX_FILE_PRIORITY_SCORE:
        raise ValueError("file-priority score must be between 0 and 100")
    if score <= 19:
        return FilePriorityLevel.LOW
    if score <= 39:
        return FilePriorityLevel.MEDIUM
    if score <= 69:
        return FilePriorityLevel.HIGH
    return FilePriorityLevel.VERY_HIGH


def calculate_file_priorities(snapshot: PullRequestSnapshot) -> tuple[list[RankedFile], FilePrioritySummary]:
    signals_by_file = _signals_by_file(snapshot.signals)
    unranked = [
        _ranked_file_without_rank(file, signals_by_file.get(file.filename, []))
        for file in snapshot.files
    ]
    ordered = sorted(
        unranked,
        key=lambda file: (
            -file.score,
            LEVEL_ORDER[file.level],
            -file.changes,
            file.path.casefold(),
            file.path,
        ),
    )
    ranked = [
        file.model_copy(update={"rank": index})
        for index, file in enumerate(ordered, start=1)
    ]
    return ranked, summarize_file_priorities(ranked)


def _ranked_file_without_rank(file: ChangedFile, signals: list[ReviewSignal]) -> RankedFile:
    factors = _apply_group_caps(
        [
            *_signal_factors(file, signals),
            *_sensitive_area_factors(file),
            *_change_size_factors(file),
            *_visibility_factors(file),
            *_rename_transition_factors(file),
        ]
    )
    score = min(MAX_FILE_PRIORITY_SCORE, sum(factor.points for factor in factors))
    return RankedFile(
        rank=1,
        path=file.filename,
        previous_path=file.previous_filename,
        status=file.status,
        score=score,
        level=level_for_file_priority(score),
        primary_kind=file.classification.primary_kind,
        areas=file.classification.areas,
        language=file.classification.language,
        changes=_file_changes(file),
        additions=max(file.additions, 0),
        deletions=max(file.deletions, 0),
        related_signal_ids=unique_sorted([signal.id for signal in signals if signal.rule_id in SIGNAL_PRIORITY_WEIGHT_BY_RULE_ID]),
        factors=sorted(factors, key=lambda factor: (FACTOR_GROUP_ORDER.index(factor.category), factor.id, factor.observed_value or "")),
        limitations=FILE_LIMITATIONS,
    )


def _signal_factors(file: ChangedFile, signals: list[ReviewSignal]) -> list[FilePriorityFactor]:
    factors: list[FilePriorityFactor] = []
    seen_rule_ids: set[str] = set()
    for signal in sorted(signals, key=lambda item: (item.rule_id, item.id)):
        weight = SIGNAL_PRIORITY_WEIGHT_BY_RULE_ID.get(signal.rule_id)
        if weight is None or signal.rule_id in seen_rule_ids:
            continue
        seen_rule_ids.add(signal.rule_id)
        factors.append(
            FilePriorityFactor(
                id=f"signal.{signal.rule_id}",
                category="signal_impact",
                points=weight.points,
                description=weight.description,
                related_signal_ids=unique_sorted([item.id for item in signals if item.rule_id == signal.rule_id]),
                observed_value=signal.rule_id,
            )
        )
    return factors


def _sensitive_area_factors(file: ChangedFile) -> list[FilePriorityFactor]:
    factors: list[FilePriorityFactor] = []
    if file.classification.primary_kind in SENSITIVE_KIND_WEIGHTS:
        factors.append(
            FilePriorityFactor(
                id=f"sensitive_kind.{file.classification.primary_kind.value}",
                category="sensitive_area",
                points=SENSITIVE_KIND_WEIGHTS[file.classification.primary_kind],
                description=f"Primary file kind is {file.classification.primary_kind.value}.",
                related_signal_ids=[],
                observed_value=file.classification.primary_kind.value,
            )
        )
    for area in sorted(file.classification.areas, key=lambda item: item.value):
        if area in SENSITIVE_AREA_WEIGHTS:
            factors.append(
                FilePriorityFactor(
                    id=f"sensitive_area.{area.value}",
                    category="sensitive_area",
                    points=SENSITIVE_AREA_WEIGHTS[area],
                    description=f"File is classified in the {area.value} area.",
                    related_signal_ids=[],
                    observed_value=area.value,
                )
            )
    return factors


def _change_size_factors(file: ChangedFile) -> list[FilePriorityFactor]:
    changes = _file_changes(file)
    points = 0
    if changes >= 1000:
        points = 15
    elif changes >= 500:
        points = 12
    elif changes >= 200:
        points = 8
    elif changes >= 50:
        points = 4
    if points == 0:
        return []
    return [
        FilePriorityFactor(
            id="change_size.changed_lines",
            category="change_size",
            points=points,
            description="Changed-line count increases review priority for this file.",
            related_signal_ids=[],
            observed_value=str(changes),
        )
    ]


def _visibility_factors(file: ChangedFile) -> list[FilePriorityFactor]:
    if file.classification.primary_kind in OPAQUE_VISIBILITY_KINDS:
        return [
            FilePriorityFactor(
                id=f"visibility.opaque_{file.classification.primary_kind.value}",
                category="visibility",
                points=5,
                description="File type has limited patch-level visibility.",
                related_signal_ids=[],
                observed_value=file.classification.primary_kind.value,
            )
        ]
    if file.patch is None and file.classification.primary_kind not in PATCH_INELIGIBLE_ASSET_KINDS:
        return [
            FilePriorityFactor(
                id="visibility.missing_patch",
                category="visibility",
                points=5,
                description="Patch text is unavailable for a patch-eligible file.",
                related_signal_ids=[],
                observed_value="missing_patch",
            )
        ]
    if any("truncated" in warning.casefold() for warning in file.classification.warnings):
        return [
            FilePriorityFactor(
                id="visibility.truncated_analysis_warning",
                category="visibility",
                points=3,
                description="File classification includes a truncation-related visibility warning.",
                related_signal_ids=[],
                observed_value="truncated_warning",
            )
        ]
    return []


def _rename_transition_factors(file: ChangedFile) -> list[FilePriorityFactor]:
    previous = file.previous_classification
    if previous is None:
        return []
    current_areas = set(file.classification.areas)
    previous_areas = set(previous.areas)
    moved_into_sensitive = bool(current_areas & RENAME_SENSITIVE_AREAS) and not bool(previous_areas & RENAME_SENSITIVE_AREAS)
    if moved_into_sensitive:
        return [
            FilePriorityFactor(
                id="rename_transition.moved_into_sensitive_area",
                category="rename_transition",
                points=5,
                description="File moved into a sensitive classified area.",
                related_signal_ids=[],
                observed_value=file.previous_filename,
            )
        ]
    if previous.primary_kind == FileKind.TEST and file.classification.primary_kind != FileKind.TEST:
        return [
            FilePriorityFactor(
                id="rename_transition.moved_out_of_test",
                category="rename_transition",
                points=4,
                description="File moved out of test classification.",
                related_signal_ids=[],
                observed_value=file.previous_filename,
            )
        ]
    if previous.primary_kind != FileKind.GENERATED and file.classification.primary_kind == FileKind.GENERATED:
        return [
            FilePriorityFactor(
                id="rename_transition.moved_into_generated",
                category="rename_transition",
                points=1,
                description="File moved into generated classification.",
                related_signal_ids=[],
                observed_value=file.previous_filename,
            )
        ]
    return []


def _apply_group_caps(factors: list[FilePriorityFactor]) -> list[FilePriorityFactor]:
    applied: list[FilePriorityFactor] = []
    for group in FACTOR_GROUP_ORDER:
        remaining = FACTOR_GROUP_CAPS[group]
        group_factors = sorted(
            [factor for factor in factors if factor.category == group],
            key=lambda factor: (-factor.points, factor.id, factor.observed_value or ""),
        )
        for factor in group_factors:
            points = min(factor.points, max(remaining, 0))
            remaining -= points
            if points > 0:
                applied.append(factor.model_copy(update={"points": points}))
    return applied


def _signals_by_file(signals: list[ReviewSignal]) -> dict[str, list[ReviewSignal]]:
    grouped: dict[str, list[ReviewSignal]] = defaultdict(list)
    for signal in signals:
        for path in unique_sorted(signal.affected_files):
            grouped[path].append(signal)
    return {
        path: sorted(items, key=lambda signal: (signal.rule_id, signal.id))
        for path, items in sorted(grouped.items(), key=lambda item: (item[0].casefold(), item[0]))
    }


def _file_changes(file: ChangedFile) -> int:
    return max(file.changes if file.changes is not None else file.additions + file.deletions, 0)
