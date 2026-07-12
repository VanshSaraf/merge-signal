from types import MappingProxyType

from app.domain.file_priority import FilePriorityLevel

LEVEL_ORDER = MappingProxyType({
    FilePriorityLevel.VERY_HIGH: 0,
    FilePriorityLevel.HIGH: 1,
    FilePriorityLevel.MEDIUM: 2,
    FilePriorityLevel.LOW: 3,
})


def unique_sorted(values: list[str] | tuple[str, ...]) -> list[str]:
    return sorted(set(values), key=lambda value: (value.casefold(), value))
