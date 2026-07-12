from types import MappingProxyType

from app.domain.review_action import ReviewAction, ReviewActionCategory, ReviewActionPriority

PRIORITY_ORDER = MappingProxyType({
    ReviewActionPriority.HIGH: 0,
    ReviewActionPriority.MEDIUM: 1,
    ReviewActionPriority.LOW: 2,
})

CATEGORY_ORDER = MappingProxyType({
    ReviewActionCategory.MERGEABILITY: 0,
    ReviewActionCategory.CI: 1,
    ReviewActionCategory.SECURITY: 2,
    ReviewActionCategory.DATABASE: 3,
    ReviewActionCategory.TESTING: 4,
    ReviewActionCategory.DEPENDENCIES: 5,
    ReviewActionCategory.CONFIGURATION: 6,
    ReviewActionCategory.INFRASTRUCTURE: 7,
    ReviewActionCategory.CHANGE_SCOPE: 8,
    ReviewActionCategory.CODE_QUALITY: 9,
    ReviewActionCategory.EVIDENCE_VISIBILITY: 10,
    ReviewActionCategory.FILE_REVIEW: 11,
})


def action_sort_key(action: ReviewAction) -> tuple[int, int, str, str]:
    return (
        PRIORITY_ORDER[action.priority],
        CATEGORY_ORDER[action.category],
        action.rule_id,
        action.id,
    )


def unique_sorted(values: list[str] | tuple[str, ...]) -> list[str]:
    return sorted(set(values), key=lambda value: (value.casefold(), value))


def unique_file_ordered(values: list[str], ranked_positions: dict[str, int]) -> list[str]:
    return sorted(set(values), key=lambda path: (ranked_positions.get(path, 10**9), path.casefold(), path))
