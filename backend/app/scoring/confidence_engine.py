from types import MappingProxyType

from app.domain.file_classification import FileKind, FileLanguage
from app.domain.pull_request import ChangedFile, CiVisibility, PullRequestSnapshot
from app.domain.scoring import ConfidenceComponent, ConfidenceComponentStatus, EvidenceConfidenceAssessment, EvidenceConfidenceLevel
from app.scoring.ordering import unique_sorted
from app.scoring.risk_rules import MAX_SCORE, SCORING_RULES_VERSION

CONFIDENCE_LIMITATIONS = [
    "Evidence confidence measures visibility and completeness, not code quality.",
    "Complete observable data can still miss semantic or runtime issues.",
]

COMPONENT_POINTS = MappingProxyType({
    "pull_request_metadata": 15,
    "changed_file_collection": 25,
    "patch_visibility": 25,
    "commit_collection": 10,
    "ci_visibility": 15,
    "classification_coverage": 10,
})

PATCH_INELIGIBLE_KINDS = frozenset({FileKind.ASSET, FileKind.BINARY, FileKind.GENERATED})


def level_for_evidence_confidence(score: int) -> EvidenceConfidenceLevel:
    if score < 0 or score > MAX_SCORE:
        raise ValueError("evidence confidence score must be between 0 and 100")
    if score <= 49:
        return EvidenceConfidenceLevel.LOW
    if score <= 79:
        return EvidenceConfidenceLevel.MEDIUM
    return EvidenceConfidenceLevel.HIGH


def calculate_evidence_confidence(snapshot: PullRequestSnapshot) -> EvidenceConfidenceAssessment:
    components = [
        _metadata_component(),
        _changed_files_component(snapshot),
        _patch_visibility_component(snapshot.files),
        _commit_collection_component(snapshot),
        _ci_visibility_component(snapshot),
        _classification_coverage_component(snapshot.files),
    ]
    warnings = _warnings_for(components)
    score = min(MAX_SCORE, sum(component.awarded_points for component in components))
    return EvidenceConfidenceAssessment(
        score=score,
        level=level_for_evidence_confidence(score),
        max_score=MAX_SCORE,
        components=components,
        warnings=warnings,
        rules_version=SCORING_RULES_VERSION,
        limitations=CONFIDENCE_LIMITATIONS,
    )


def _metadata_component() -> ConfidenceComponent:
    return ConfidenceComponent(
        id="pull_request_metadata",
        name="Pull-request metadata",
        maximum_points=COMPONENT_POINTS["pull_request_metadata"],
        awarded_points=15,
        status=ConfidenceComponentStatus.COMPLETE,
        explanation="Core normalized pull-request metadata is present.",
        limitations=["Snapshot creation requires valid core metadata."],
    )


def _changed_files_component(snapshot: PullRequestSnapshot) -> ConfidenceComponent:
    maximum = COMPONENT_POINTS["changed_file_collection"]
    if snapshot.completeness.files_complete:
        awarded = maximum
        status = ConfidenceComponentStatus.COMPLETE
        explanation = "Changed-file collection completed."
        limitations: list[str] = []
    elif snapshot.files:
        awarded = 10
        status = ConfidenceComponentStatus.PARTIAL
        explanation = "Changed-file collection is incomplete, but some files were retrieved."
        limitations = ["Signal detection only covers retrieved files."]
    else:
        awarded = 0
        status = ConfidenceComponentStatus.UNAVAILABLE
        explanation = "Changed-file collection is unavailable."
        limitations = ["File-based signals cannot be evaluated without changed files."]
    return ConfidenceComponent(
        id="changed_file_collection",
        name="Changed-file collection",
        maximum_points=maximum,
        awarded_points=awarded,
        status=status,
        explanation=explanation,
        limitations=limitations,
    )


def _patch_visibility_component(files: list[ChangedFile]) -> ConfidenceComponent:
    maximum = COMPONENT_POINTS["patch_visibility"]
    eligible = [file for file in files if _is_patch_eligible(file)]
    if not eligible:
        return ConfidenceComponent(
            id="patch_visibility",
            name="Patch visibility",
            maximum_points=maximum,
            awarded_points=maximum,
            status=ConfidenceComponentStatus.NOT_APPLICABLE,
            explanation="No patch-eligible files were present, so patch absence is treated neutrally.",
            limitations=["Binary, generated, and asset files are excluded from patch-coverage expectations."],
        )

    visible = sum(1 for file in eligible if file.patch is not None)
    awarded = _coverage_points(visible, len(eligible), [(100, 25), (80, 20), (50, 12), (1, 5)], maximum)
    status = ConfidenceComponentStatus.COMPLETE if visible == len(eligible) else ConfidenceComponentStatus.PARTIAL
    return ConfidenceComponent(
        id="patch_visibility",
        name="Patch visibility",
        maximum_points=maximum,
        awarded_points=awarded,
        status=status,
        explanation=f"Patch text is available for {visible} of {len(eligible)} patch-eligible files.",
        limitations=[] if status == ConfidenceComponentStatus.COMPLETE else ["Patch-based signals may be incomplete for eligible files without patch text."],
    )


def _commit_collection_component(snapshot: PullRequestSnapshot) -> ConfidenceComponent:
    maximum = COMPONENT_POINTS["commit_collection"]
    if snapshot.completeness.commits_complete:
        return ConfidenceComponent(
            id="commit_collection",
            name="Commit collection",
            maximum_points=maximum,
            awarded_points=maximum,
            status=ConfidenceComponentStatus.COMPLETE,
            explanation="Commit collection completed.",
            limitations=[],
        )
    if snapshot.commits:
        return ConfidenceComponent(
            id="commit_collection",
            name="Commit collection",
            maximum_points=maximum,
            awarded_points=4,
            status=ConfidenceComponentStatus.PARTIAL,
            explanation="Commit collection is incomplete, but some commits were retrieved.",
            limitations=["Commit-derived signals only cover retrieved commit metadata."],
        )
    return ConfidenceComponent(
        id="commit_collection",
        name="Commit collection",
        maximum_points=maximum,
        awarded_points=0,
        status=ConfidenceComponentStatus.UNAVAILABLE,
        explanation="Commit collection is unavailable.",
        limitations=["Commit-derived signals cannot be evaluated without commits."],
    )


def _ci_visibility_component(snapshot: PullRequestSnapshot) -> ConfidenceComponent:
    maximum = COMPONENT_POINTS["ci_visibility"]
    if snapshot.ci.visibility == CiVisibility.COMPLETE:
        return ConfidenceComponent(
            id="ci_visibility",
            name="CI visibility",
            maximum_points=maximum,
            awarded_points=maximum,
            status=ConfidenceComponentStatus.COMPLETE,
            explanation="CI visibility is complete for observed check-run and commit-status surfaces.",
            limitations=[],
        )
    if snapshot.ci.visibility == CiVisibility.PARTIAL:
        return ConfidenceComponent(
            id="ci_visibility",
            name="CI visibility",
            maximum_points=maximum,
            awarded_points=8,
            status=ConfidenceComponentStatus.PARTIAL,
            explanation="CI visibility is partial.",
            limitations=["Some check-run or commit-status records may be absent."],
        )
    return ConfidenceComponent(
        id="ci_visibility",
        name="CI visibility",
        maximum_points=maximum,
        awarded_points=0,
        status=ConfidenceComponentStatus.UNAVAILABLE,
        explanation="CI visibility is unavailable.",
        limitations=["CI-related signals are limited when CI surfaces are unavailable."],
    )


def _classification_coverage_component(files: list[ChangedFile]) -> ConfidenceComponent:
    maximum = COMPONENT_POINTS["classification_coverage"]
    if not files:
        return ConfidenceComponent(
            id="classification_coverage",
            name="Classification coverage",
            maximum_points=maximum,
            awarded_points=maximum,
            status=ConfidenceComponentStatus.NOT_APPLICABLE,
            explanation="No changed files were present.",
            limitations=[],
        )
    classified = sum(1 for file in files if _meaningfully_classified(file))
    awarded = _coverage_points(classified, len(files), [(100, 10), (80, 8), (50, 5), (1, 2)], maximum)
    status = ConfidenceComponentStatus.COMPLETE if classified == len(files) else ConfidenceComponentStatus.PARTIAL
    return ConfidenceComponent(
        id="classification_coverage",
        name="Classification coverage",
        maximum_points=maximum,
        awarded_points=awarded,
        status=status,
        explanation=f"{classified} of {len(files)} changed files have a known kind or language.",
        limitations=[] if status == ConfidenceComponentStatus.COMPLETE else ["Classification coverage is limited for unknown file types."],
    )


def _coverage_points(observed: int, total: int, bands: list[tuple[int, int]], maximum: int) -> int:
    if total <= 0:
        return maximum
    coverage = observed * 100 // total
    for threshold, points in bands:
        if coverage >= threshold:
            return points
    return 0


def _is_patch_eligible(file: ChangedFile) -> bool:
    return file.classification.primary_kind not in PATCH_INELIGIBLE_KINDS


def _meaningfully_classified(file: ChangedFile) -> bool:
    return file.classification.primary_kind != FileKind.UNKNOWN or file.classification.language != FileLanguage.UNKNOWN


def _warnings_for(components: list[ConfidenceComponent]) -> list[str]:
    warnings: list[str] = []
    for component in components:
        if component.id == "changed_file_collection" and component.status != ConfidenceComponentStatus.COMPLETE:
            warnings.append("Changed-file collection is incomplete.")
        if component.id == "patch_visibility" and component.status == ConfidenceComponentStatus.PARTIAL:
            warnings.append("Patch visibility is partial for eligible files.")
        if component.id == "commit_collection" and component.status != ConfidenceComponentStatus.COMPLETE:
            warnings.append("Commit collection is incomplete.")
        if component.id == "ci_visibility" and component.status == ConfidenceComponentStatus.PARTIAL:
            warnings.append("CI visibility is partial.")
        if component.id == "ci_visibility" and component.status == ConfidenceComponentStatus.UNAVAILABLE:
            warnings.append("CI visibility is unavailable.")
        if component.id == "classification_coverage" and component.status == ConfidenceComponentStatus.PARTIAL:
            warnings.append("Classification coverage is limited.")
    return unique_sorted(warnings)
