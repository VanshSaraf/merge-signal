from dataclasses import dataclass
from enum import StrEnum


MAX_PATCH_CHARACTERS = 200_000
MAX_PATCH_LINES = 10_000
MAX_SAFE_LINE_LENGTH = 10_000


class PatchLineKind(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    CONTEXT = "context"
    METADATA = "metadata"


@dataclass(frozen=True)
class PatchLine:
    kind: PatchLineKind
    content: str
    hunk_index: int
    position: int


@dataclass(frozen=True)
class ParsedPatch:
    lines: tuple[PatchLine, ...]
    warnings: tuple[str, ...]
    truncated: bool


def parse_patch(patch: str | None) -> ParsedPatch:
    if not patch:
        return ParsedPatch(lines=(), warnings=(), truncated=False)

    warnings: list[str] = []
    truncated = False
    scanned = patch
    if len(scanned) > MAX_PATCH_CHARACTERS:
        scanned = scanned[:MAX_PATCH_CHARACTERS]
        truncated = True
        warnings.append("Patch scanning was truncated by character limit.")

    raw_lines = scanned.splitlines()
    if len(raw_lines) > MAX_PATCH_LINES:
        raw_lines = raw_lines[:MAX_PATCH_LINES]
        truncated = True
        warnings.append("Patch scanning was truncated by line limit.")

    lines: list[PatchLine] = []
    hunk_index = -1
    hunk_position = 0

    for raw_line in raw_lines:
        line = raw_line[:MAX_SAFE_LINE_LENGTH]
        if len(raw_line) > MAX_SAFE_LINE_LENGTH:
            truncated = True
            warnings.append("One or more patch lines were truncated by safe line-length limit.")

        if line.startswith("@@"):
            hunk_index += 1
            hunk_position = 0
            lines.append(PatchLine(PatchLineKind.METADATA, "", hunk_index, hunk_position))
            continue
        if line.startswith(("+++", "---", "diff ", "index ", "new file mode", "deleted file mode")):
            lines.append(PatchLine(PatchLineKind.METADATA, "", max(hunk_index, 0), hunk_position))
            continue

        hunk_position += 1
        current_hunk = max(hunk_index, 0)
        if line.startswith("+"):
            lines.append(PatchLine(PatchLineKind.ADDED, line[1:], current_hunk, hunk_position))
        elif line.startswith("-"):
            lines.append(PatchLine(PatchLineKind.REMOVED, line[1:], current_hunk, hunk_position))
        else:
            content = line[1:] if line.startswith(" ") else line
            lines.append(PatchLine(PatchLineKind.CONTEXT, content, current_hunk, hunk_position))

    return ParsedPatch(lines=tuple(lines), warnings=tuple(sorted(set(warnings))), truncated=truncated)


def added_lines_by_hunk(parsed: ParsedPatch) -> dict[int, list[PatchLine]]:
    grouped: dict[int, list[PatchLine]] = {}
    for line in parsed.lines:
        if line.kind == PatchLineKind.ADDED:
            grouped.setdefault(line.hunk_index, []).append(line)
    return grouped
