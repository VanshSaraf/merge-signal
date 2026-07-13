from urllib.parse import quote, urlparse

from app.domain.pull_request import (
    BriefingSourceType,
    CiState,
    CiVisibility,
    PullRequestSnapshot,
    ReviewBriefing,
    ReviewBriefingFocusItem,
    ReviewBriefingPriorityFile,
    ReviewBriefingProvenance,
    ReviewBriefingReason,
    ReviewBriefingStep,
    ReviewConcernAttentionState,
)
from app.domain.review_action import ReviewAction
from app.domain.review_signal import SignalSeverity

MAX_FOCUS_ITEMS = 3
MAX_PRIORITY_FILES = 3
MAX_STEPS = 5
MAX_LIMITATIONS = 3


def build_review_briefing(snapshot: PullRequestSnapshot) -> ReviewBriefing:
    focus = _dedupe_focus(
        [
            *_ci_focus(snapshot),
            *_review_concern_focus(snapshot),
            *_signal_focus(snapshot),
            *_evidence_focus(snapshot),
            *_priority_file_focus(snapshot),
        ]
    )[:MAX_FOCUS_ITEMS]
    priority_files = _priority_files(snapshot)
    steps = _recommended_steps(snapshot, focus, priority_files)
    primary_reason = _primary_reason(snapshot, focus)
    checklist = _checklist(snapshot, steps)
    limitations = _limitations(snapshot)
    return ReviewBriefing(
        status=snapshot.merge_readiness.decision.value,
        headline=_headline(snapshot, primary_reason),
        summary=_summary(snapshot, focus, priority_files),
        primary_reason=primary_reason,
        review_focus=focus,
        priority_files=priority_files,
        recommended_steps=steps,
        checklist=checklist,
        limitations=limitations,
        provenance=_provenance(primary_reason, focus, priority_files, steps),
    )


def _ci_focus(snapshot: PullRequestSnapshot) -> list[ReviewBriefingFocusItem]:
    items: list[ReviewBriefingFocusItem] = []
    for item in snapshot.ci_explanation.blocking_items:
        identifier = _ci_item_id(item.provider, item.name, item.source_type.value)
        items.append(
            ReviewBriefingFocusItem(
                title=f"Inspect failed {item.provider} { _category_label(item.category.value) } check",
                description=item.description or f"{item.name} is currently failing.",
                severity="high",
                source_type=BriefingSourceType.CI,
                affected_files=[],
                url=_safe_url(item.details_url),
                provenance=[identifier],
            )
        )
    if not items and snapshot.ci.state == CiState.PENDING:
        items.append(
            ReviewBriefingFocusItem(
                title="Wait for pending CI checks",
                description=snapshot.ci_explanation.summary,
                severity="medium",
                source_type=BriefingSourceType.CI,
                affected_files=[],
                url=None,
                provenance=["ci.pending"],
            )
        )
    return items


def _review_concern_focus(snapshot: PullRequestSnapshot) -> list[ReviewBriefingFocusItem]:
    items: list[ReviewBriefingFocusItem] = []
    for thread in snapshot.review_context.threads:
        if thread.lifecycle.attention_state == ReviewConcernAttentionState.OUTDATED:
            continue
        if thread.lifecycle.has_reviewer_follow_up:
            items.append(_thread_focus(thread, "Review the latest reviewer follow-up", "A reviewer followed up after the latest author response.", "high"))
        elif thread.lifecycle.active_latest_change_request:
            items.append(_thread_focus(thread, "Address the active reviewer change request", "The latest observable reviewer state still requests changes.", "high"))
        elif thread.lifecycle.attention_state == ReviewConcernAttentionState.AWAITING_AUTHOR_RESPONSE:
            items.append(_thread_focus(thread, "Respond to reviewer concern", "A reviewer concern is awaiting an author response.", "medium"))
        elif thread.lifecycle.author_claimed_addressed:
            items.append(_thread_focus(thread, "Verify the author's claimed fix", "The author claims this concern was addressed; MergeSignal has not verified the code change.", "medium"))
    return sorted(items, key=lambda item: (_severity_order(item.severity), item.affected_files, item.title))


def _thread_focus(thread, title: str, description: str, severity: str) -> ReviewBriefingFocusItem:
    return ReviewBriefingFocusItem(
        title=title,
        description=description,
        severity=severity,
        source_type=BriefingSourceType.REVIEW_CONCERN,
        affected_files=[thread.path] if thread.path else [],
        url=_safe_url(thread.html_url),
        provenance=[thread.id],
    )


def _signal_focus(snapshot: PullRequestSnapshot) -> list[ReviewBriefingFocusItem]:
    signals = [
        signal
        for signal in snapshot.signals
        if signal.severity == SignalSeverity.HIGH
    ]
    return [
        ReviewBriefingFocusItem(
            title=signal.title,
            description=signal.description,
            severity=signal.severity.value,
            source_type=BriefingSourceType.REVIEW_SIGNAL,
            affected_files=signal.affected_files,
            url=None,
            provenance=[signal.id],
        )
        for signal in sorted(signals, key=lambda item: (_severity_order(item.severity.value), item.rule_id, item.id))
    ]


def _evidence_focus(snapshot: PullRequestSnapshot) -> list[ReviewBriefingFocusItem]:
    items: list[ReviewBriefingFocusItem] = []
    if snapshot.evidence_confidence.score < 70:
        items.append(
            ReviewBriefingFocusItem(
                title="Inspect incomplete evidence",
                description=f"Evidence confidence is {snapshot.evidence_confidence.score}/100; unsupported sources were not analyzed.",
                severity="medium",
                source_type=BriefingSourceType.EVIDENCE,
                affected_files=[],
                url=None,
                provenance=["evidence_confidence"],
            )
        )
    if snapshot.ci.visibility in {CiVisibility.PARTIAL, CiVisibility.UNAVAILABLE}:
        items.append(
            ReviewBriefingFocusItem(
                title="Investigate CI visibility",
                description=f"CI visibility is {snapshot.ci.visibility.value}.",
                severity="medium",
                source_type=BriefingSourceType.EVIDENCE,
                affected_files=[],
                url=None,
                provenance=[f"ci_visibility:{snapshot.ci.visibility.value}"],
            )
        )
    return items


def _priority_file_focus(snapshot: PullRequestSnapshot) -> list[ReviewBriefingFocusItem]:
    if not snapshot.ranked_files:
        return []
    file = snapshot.ranked_files[0]
    if file.level.value not in {"high", "very_high"}:
        return []
    return [
        ReviewBriefingFocusItem(
            title=f"Review {file.path} first",
            description=_file_reason_text(file),
            severity="medium" if file.level.value in {"high", "very_high"} else "low",
            source_type=BriefingSourceType.FILE_PRIORITY,
            affected_files=[file.path],
            url=_file_url(snapshot, file.path),
            provenance=[file.path],
        )
    ]


def _priority_files(snapshot: PullRequestSnapshot) -> list[ReviewBriefingPriorityFile]:
    return [
        ReviewBriefingPriorityFile(
            path=file.path,
            rank=file.rank,
            score=file.score,
            level=file.level.value,
            reasons=[factor.description for factor in file.factors[:2]],
            url=_file_url(snapshot, file.path),
        )
        for file in sorted(snapshot.ranked_files, key=lambda item: item.rank)[:MAX_PRIORITY_FILES]
    ]


def _recommended_steps(
    snapshot: PullRequestSnapshot,
    focus: list[ReviewBriefingFocusItem],
    priority_files: list[ReviewBriefingPriorityFile],
) -> list[ReviewBriefingStep]:
    steps: list[ReviewBriefingStep] = []
    seen: set[str] = set()
    for item in focus:
        _append_step(
            steps,
            seen,
            title=_imperative_title(item.title),
            description=item.description,
            category=item.source_type.value,
            affected_files=item.affected_files,
            url=item.url,
            source_ids=item.provenance,
        )
    for action in snapshot.review_actions:
        _append_action_step(steps, seen, action)
        if len(steps) >= MAX_STEPS:
            break
    for file in priority_files:
        _append_step(
            steps,
            seen,
            title=f"Review {file.path}",
            description="; ".join(file.reasons) or f"{file.level} priority changed file.",
            category="file_priority",
            affected_files=[file.path],
            url=file.url,
            source_ids=[file.path],
        )
    return [step.model_copy(update={"order": index}) for index, step in enumerate(steps[:MAX_STEPS], start=1)]


def _append_action_step(steps: list[ReviewBriefingStep], seen: set[str], action: ReviewAction) -> None:
    url = _url_from_evidence(action.evidence)
    _append_step(
        steps,
        seen,
        title=_imperative_title(action.title),
        description=action.description,
        category=action.category.value,
        affected_files=action.affected_files,
        url=url,
        source_ids=[action.id, action.rule_id],
    )


def _append_step(
    steps: list[ReviewBriefingStep],
    seen: set[str],
    *,
    title: str,
    description: str,
    category: str,
    affected_files: list[str],
    url: str | None,
    source_ids: list[str],
) -> None:
    key = f"{category}:{','.join(source_ids)}:{','.join(affected_files)}"
    if key in seen or len(steps) >= MAX_STEPS:
        return
    seen.add(key)
    steps.append(
        ReviewBriefingStep(
            order=len(steps) + 1,
            title=title,
            description=description,
            category=category,
            affected_files=affected_files,
            url=url,
            source_ids=source_ids,
        )
    )


def _primary_reason(snapshot: PullRequestSnapshot, focus: list[ReviewBriefingFocusItem]) -> ReviewBriefingReason | None:
    if focus:
        item = focus[0]
        return ReviewBriefingReason(
            title=item.title,
            category=item.source_type.value,
            severity=item.severity,
            source_type=item.source_type,
            source_ids=item.provenance,
            affected_files=item.affected_files,
            url=item.url,
        )
    reason = snapshot.merge_readiness.reasons[0] if snapshot.merge_readiness.reasons else None
    if reason is None:
        return None
    return ReviewBriefingReason(
        title=reason.title,
        category="readiness",
        severity=reason.effect.value,
        source_type=BriefingSourceType.READINESS,
        source_ids=[reason.rule_id],
        affected_files=reason.affected_files,
        url=None,
    )


def _headline(snapshot: PullRequestSnapshot, primary: ReviewBriefingReason | None) -> str:
    status = snapshot.merge_readiness.decision.value
    if primary and primary.source_type == BriefingSourceType.CI and status == "blocked":
        return f"Blocked by {primary.title.removeprefix('Inspect ').lower()}."
    if snapshot.ci.state == CiState.PENDING:
        count = snapshot.ci.pending_count or snapshot.ci_explanation.pending_count
        return f"Not ready while {count} {_plural(count, 'check is', 'checks are')} pending."
    if status == "ready_with_caution" and primary:
        return f"Ready with caution because {primary.title.lower()}."
    if status == "ready":
        suffix = "currently visible evidence"
        if snapshot.evidence_confidence.score < 100:
            suffix = "the currently visible evidence, with noted evidence limits"
        return f"Ready based on {suffix}."
    if primary:
        return f"{_title_status(status)} because {primary.title.lower()}."
    return f"{_title_status(status)} based on the currently visible evidence."


def _summary(snapshot: PullRequestSnapshot, focus: list[ReviewBriefingFocusItem], files: list[ReviewBriefingPriorityFile]) -> str:
    parts = [
        f"{_title_status(snapshot.merge_readiness.decision.value)} readiness",
        f"{snapshot.merge_risk.score}/100 merge risk",
        f"{snapshot.evidence_confidence.score}/100 evidence confidence",
    ]
    if focus:
        parts.append(f"{len(focus)} review focus {_plural(len(focus), 'item', 'items')}")
    if files:
        parts.append(f"start with {files[0].path}")
    return "; ".join(parts) + "."


def _checklist(snapshot: PullRequestSnapshot, steps: list[ReviewBriefingStep]) -> list[str]:
    header = [
        "MergeSignal Review Checklist",
        f"PR: {snapshot.reference.owner}/{snapshot.reference.repository}#{snapshot.reference.pull_number}",
        f"Status: {_title_status(snapshot.merge_readiness.decision.value)}",
    ]
    return [*header, *[f"[ ] {step.title}" for step in steps[:MAX_STEPS]]]


def _limitations(snapshot: PullRequestSnapshot) -> list[str]:
    limits = ["Human review remains necessary."]
    if snapshot.evidence_confidence.score < 100:
        limits.append("Evidence confidence measures visibility, not code quality.")
    if snapshot.review_context.thread_count:
        limits.append("Review-concern lifecycle does not prove formal resolution.")
    return limits[:MAX_LIMITATIONS]


def _provenance(
    primary: ReviewBriefingReason | None,
    focus: list[ReviewBriefingFocusItem],
    files: list[ReviewBriefingPriorityFile],
    steps: list[ReviewBriefingStep],
) -> ReviewBriefingProvenance:
    source_ids = [*(primary.source_ids if primary else []), *[id for item in focus for id in item.provenance], *[id for step in steps for id in step.source_ids]]
    return ReviewBriefingProvenance(
        readiness_reason_ids=sorted(id for id in set(source_ids) if id.startswith("readiness.")),
        ci_item_ids=sorted(id for id in set(source_ids) if id.startswith("ci:") or id.startswith("ci.")),
        signal_ids=sorted(id for id in set(source_ids) if id.startswith("sig") or ":fixture" in id),
        action_ids=sorted(id for id in set(source_ids) if id.startswith("action.")),
        file_paths=sorted({file.path for file in files} | {path for item in focus for path in item.affected_files} | {path for step in steps for path in step.affected_files}),
        review_thread_ids=sorted(id for id in set(source_ids) if id.startswith("review-thread-")),
    )


def _dedupe_focus(items: list[ReviewBriefingFocusItem]) -> list[ReviewBriefingFocusItem]:
    deduped: list[ReviewBriefingFocusItem] = []
    seen: set[str] = set()
    for item in sorted(items, key=lambda item: (_source_order(item.source_type), _severity_order(item.severity), item.title, item.affected_files)):
        key = ",".join(item.provenance) or f"{item.source_type}:{','.join(item.affected_files)}:{item.title}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _file_reason_text(file) -> str:
    return "; ".join(factor.description for factor in file.factors[:2]) or f"{file.level.value} priority changed file."


def _file_url(snapshot: PullRequestSnapshot, path: str) -> str | None:
    changed = next((file for file in snapshot.files if file.filename == path), None)
    if changed and (url := _safe_url(changed.blob_url)):
        return url
    if not snapshot.metadata.head_sha:
        return None
    encoded_path = quote(path, safe="/")
    return _safe_url(f"https://github.com/{snapshot.reference.owner}/{snapshot.reference.repository}/blob/{snapshot.metadata.head_sha}/{encoded_path}")


def _url_from_evidence(evidence: list[str]) -> str | None:
    for item in evidence:
        marker = "Details URL: "
        if item.startswith(marker):
            return _safe_url(item.removeprefix(marker).strip())
    return None


def _safe_url(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    if parsed.scheme != "https" or parsed.username or parsed.password or not parsed.netloc:
        return None
    return value


def _imperative_title(title: str) -> str:
    return title.rstrip(".")


def _category_label(category: str) -> str:
    if category == "authorization_or_configuration":
        return "authorization/configuration"
    return category.replace("_", " ")


def _ci_item_id(provider: str, name: str, source_type: str) -> str:
    return f"ci:{source_type}:{provider}:{name}"


def _severity_order(value: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3, "block": 0, "require_resolution": 1, "caution": 2}.get(value, 4)


def _source_order(value: BriefingSourceType) -> int:
    return {
        BriefingSourceType.READINESS: 0,
        BriefingSourceType.CI: 1,
        BriefingSourceType.REVIEW_CONCERN: 2,
        BriefingSourceType.REVIEW_SIGNAL: 3,
        BriefingSourceType.EVIDENCE: 4,
        BriefingSourceType.FILE_PRIORITY: 5,
        BriefingSourceType.REVIEW_ACTION: 6,
    }[value]


def _title_status(value: str) -> str:
    return value.replace("_", " ").title()


def _plural(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural
