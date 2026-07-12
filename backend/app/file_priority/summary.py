from collections import Counter

from app.domain.file_priority import FilePriorityCount, FilePriorityLevel, FilePrioritySummary, RankedFile
from app.file_priority.rules import FILE_PRIORITY_RULES_VERSION

SUMMARY_LIMITATIONS = [
    "Review priority is a deterministic ordering heuristic, not merge risk.",
    "A high-priority file is not proven defective.",
    "A low-priority file must not be ignored.",
]


def summarize_file_priorities(ranked_files: list[RankedFile]) -> FilePrioritySummary:
    counts = Counter(file.level for file in ranked_files)
    return FilePrioritySummary(
        total_files=len(ranked_files),
        counts_by_level=[
            FilePriorityCount(name=level.value, count=counts[level])
            for level in FilePriorityLevel
            if counts[level] > 0
        ],
        highest_priority_files=[file.path for file in ranked_files[:10]],
        files_with_signal_factors=sum(
            1 for file in ranked_files if any(factor.category == "signal_impact" for factor in file.factors)
        ),
        files_with_limited_patch_visibility=sum(
            1 for file in ranked_files if any(factor.category == "visibility" for factor in file.factors)
        ),
        rules_version=FILE_PRIORITY_RULES_VERSION,
        limitations=SUMMARY_LIMITATIONS,
    )
