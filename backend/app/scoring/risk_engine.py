from collections import defaultdict

from app.domain.review_signal import ReviewSignal
from app.domain.scoring import MergeRiskAssessment, MergeRiskLevel, RiskContribution, RiskGroup, RiskGroupScore
from app.scoring.ordering import GROUP_ORDER, SEVERITY_ORDER, unique_sorted
from app.scoring.risk_rules import MAX_SCORE, RISK_GROUP_CAPS, RISK_GROUP_ORDER, RISK_RULE_BY_ID, SCORING_RULES_VERSION

RISK_LIMITATIONS = [
    "Merge risk is a deterministic heuristic, not a probability.",
    "Merge risk is not a merge decision and does not prove a pull request contains a defect.",
    "A low merge-risk score does not mean a pull request is safe.",
]


def level_for_merge_risk(score: int) -> MergeRiskLevel:
    if score < 0 or score > MAX_SCORE:
        raise ValueError("merge risk score must be between 0 and 100")
    if score <= 24:
        return MergeRiskLevel.LOW
    if score <= 49:
        return MergeRiskLevel.MODERATE
    if score <= 74:
        return MergeRiskLevel.HIGH
    return MergeRiskLevel.VERY_HIGH


def calculate_merge_risk(signals: list[ReviewSignal]) -> MergeRiskAssessment:
    candidates: dict[RiskGroup, list[RiskContribution]] = defaultdict(list)
    non_scoring_count = 0

    for signal in signals:
        configured = RISK_RULE_BY_ID.get(signal.rule_id)
        if configured is None or configured.points == 0:
            non_scoring_count += 1
            continue
        candidates[configured.group].append(
            RiskContribution(
                signal_id=signal.id,
                rule_id=signal.rule_id,
                group=configured.group,
                title=signal.title,
                severity=signal.severity,
                raw_points=configured.points,
                applied_points=configured.points,
                capped=False,
                affected_files=unique_sorted(signal.affected_files),
                explanation=f"Observed signal '{signal.rule_id}' contributes to {configured.group.value} risk.",
            )
        )

    contributions: list[RiskContribution] = []
    group_scores: list[RiskGroupScore] = []

    for group in RISK_GROUP_ORDER:
        ordered = sorted(
            candidates[group],
            key=lambda contribution: (
                -contribution.raw_points,
                SEVERITY_ORDER[contribution.severity],
                contribution.rule_id,
                contribution.signal_id,
            ),
        )
        cap = RISK_GROUP_CAPS[group]
        remaining = cap
        applied_group_points = 0
        raw_group_points = sum(contribution.raw_points for contribution in ordered)
        for contribution in ordered:
            applied = min(contribution.raw_points, max(remaining, 0))
            remaining -= applied
            applied_group_points += applied
            contributions.append(
                contribution.model_copy(
                    update={
                        "applied_points": applied,
                        "capped": applied < contribution.raw_points,
                    }
                )
            )
        group_scores.append(
            RiskGroupScore(
                group=group,
                raw_points=raw_group_points,
                applied_points=applied_group_points,
                cap=cap,
                capped_points=raw_group_points - applied_group_points,
                contribution_count=len(ordered),
            )
        )

    contributions = sorted(
        contributions,
        key=lambda contribution: (
            GROUP_ORDER[contribution.group],
            -contribution.raw_points,
            SEVERITY_ORDER[contribution.severity],
            contribution.rule_id,
            contribution.signal_id,
        ),
    )
    score = min(MAX_SCORE, sum(group.applied_points for group in group_scores))
    return MergeRiskAssessment(
        score=score,
        level=level_for_merge_risk(score),
        max_score=MAX_SCORE,
        group_scores=group_scores,
        contributions=contributions,
        contributing_signal_count=len(contributions),
        non_scoring_signal_count=non_scoring_count,
        rules_version=SCORING_RULES_VERSION,
        limitations=RISK_LIMITATIONS,
    )
