from collections import Counter

from app.domain.review_signal import (
    EvidenceKind,
    ReviewSignal,
    ReviewSignalSummary,
    SignalCategory,
    SignalCount,
    SignalSeverity,
)
from app.signals.rules import RULES_VERSION


def build_signal_summary(signals: list[ReviewSignal], warnings: list[str] | None = None) -> ReviewSignalSummary:
    severity_counts = Counter(signal.severity for signal in signals)
    category_counts = Counter(signal.category for signal in signals)
    files_with_signals = sorted(
        {file for signal in signals for file in signal.affected_files},
        key=lambda value: (value.casefold(), value),
    )
    high_attention_files = sorted(
        {file for signal in signals if signal.severity == SignalSeverity.HIGH for file in signal.affected_files},
        key=lambda value: (value.casefold(), value),
    )

    return ReviewSignalSummary(
        total_signals=len(signals),
        counts_by_severity=[
            SignalCount(name=severity.value, count=severity_counts[severity])
            for severity in SignalSeverity
            if severity_counts[severity] > 0
        ],
        counts_by_category=[
            SignalCount(name=category.value, count=category_counts[category])
            for category in SignalCategory
            if category_counts[category] > 0
        ],
        files_with_signals=files_with_signals,
        high_attention_files=high_attention_files,
        patch_based_signal_count=sum(
            1 for signal in signals if any(evidence.kind == EvidenceKind.PATCH_PATTERN for evidence in signal.evidence)
        ),
        metadata_signal_count=sum(1 for signal in signals if signal.category == SignalCategory.METADATA),
        ci_signal_count=sum(1 for signal in signals if signal.category == SignalCategory.CI),
        warnings=sorted(set(warnings or [])),
        rules_version=RULES_VERSION,
    )
