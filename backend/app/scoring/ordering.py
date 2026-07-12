from types import MappingProxyType

from app.domain.review_signal import SignalSeverity
from app.domain.scoring import RiskGroup
from app.scoring.risk_rules import RISK_GROUP_ORDER

SEVERITY_ORDER = MappingProxyType({
    SignalSeverity.HIGH: 0,
    SignalSeverity.MEDIUM: 1,
    SignalSeverity.LOW: 2,
    SignalSeverity.INFO: 3,
})

GROUP_ORDER = MappingProxyType({group: index for index, group in enumerate(RISK_GROUP_ORDER)})


def unique_sorted(values: list[str] | tuple[str, ...]) -> list[str]:
    return sorted(set(values), key=lambda value: (value.casefold(), value))
