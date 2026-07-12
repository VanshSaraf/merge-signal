from collections import Counter

from app.domain.review_action import (
    ReviewAction,
    ReviewActionCategory,
    ReviewActionCount,
    ReviewActionPriority,
    ReviewActionSummary,
)
from app.review_actions.ordering import unique_sorted
from app.review_actions.rules import REVIEW_ACTION_RULES_VERSION

SUMMARY_LIMITATIONS = [
    "Actions are deterministic review prompts, not AI commentary.",
    "Actions do not prove a defect.",
    "Actions do not modify code or assign reviewers.",
    "Human judgment remains required.",
]


def summarize_review_actions(actions: list[ReviewAction]) -> ReviewActionSummary:
    priorities = Counter(action.priority for action in actions)
    categories = Counter(action.category for action in actions)
    affected_files = unique_sorted([path for action in actions for path in action.affected_files])
    return ReviewActionSummary(
        total_actions=len(actions),
        counts_by_priority=[
            ReviewActionCount(name=priority.value, count=priorities[priority])
            for priority in ReviewActionPriority
            if priorities[priority] > 0
        ],
        counts_by_category=[
            ReviewActionCount(name=category.value, count=categories[category])
            for category in ReviewActionCategory
            if categories[category] > 0
        ],
        affected_file_count=len(affected_files),
        high_priority_action_count=priorities[ReviewActionPriority.HIGH],
        rules_version=REVIEW_ACTION_RULES_VERSION,
        limitations=SUMMARY_LIMITATIONS,
    )
