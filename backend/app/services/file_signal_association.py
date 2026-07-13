from app.domain.pull_request import ChangedFile
from app.domain.review_signal import ReviewSignal


def normalize_repo_path(value: str | None) -> str:
    return str(value or "").strip().replace("\\", "/").lstrip("./")


def signals_for_changed_file(file: ChangedFile, signals: list[ReviewSignal]) -> list[ReviewSignal]:
    current = normalize_repo_path(file.filename)
    previous = normalize_repo_path(file.previous_filename)
    matched: dict[str, ReviewSignal] = {}
    for signal in signals:
        affected = {normalize_repo_path(path) for path in signal.affected_files}
        if current and current in affected:
            matched.setdefault(signal.id, signal)
        elif previous and previous in affected:
            matched.setdefault(signal.id, signal)
    return sorted(matched.values(), key=lambda signal: (signal.rule_id, signal.id))
