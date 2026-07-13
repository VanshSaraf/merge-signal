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
from app.services.ci_explanation import actionable_ci_description, actionable_ci_title

MAX_FOCUS_ITEMS = 3
MAX_PRIORITY_FILES = 3
MAX_STEPS = 5
MAX_LIMITATIONS = 3


def build_review_briefing(snapshot: PullRequestSnapshot) -> ReviewBriefing:
    canonical_ci_ids = {_canonical_ci_item_id(item) for item in snapshot.ci_explanation.blocking_items}
    focus = _dedupe_focus(
        [
            *_ci_focus(snapshot),
            *_review_concern_focus(snapshot),
            *_signal_focus(snapshot, suppress_generic_ci=bool(canonical_ci_ids)),
            *_evidence_focus(snapshot),
            *_priority_file_focus(snapshot),
        ]
    )[:MAX_FOCUS_ITEMS]
    priority_files = _priority_files(snapshot)
    steps = _recommended_steps(snapshot, focus, priority_files, canonical_ci_ids)
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
    grouped: dict[str, list] = {}
    for item in snapshot.ci_explanation.blocking_items:
        grouped.setdefault(_canonical_ci_concern_key(item), []).append(item)
    items: list[ReviewBriefingFocusItem] = []
    for _, ci_items in sorted(grouped.items(), key=lambda entry: entry[0]):
        item = ci_items[0]
        identifiers = sorted({_canonical_ci_item_id(candidate) for candidate in ci_items})
        items.append(
            ReviewBriefingFocusItem(
                title=actionable_ci_title(item),
                description=actionable_ci_description(ci_items),
                severity="high",
                source_type=BriefingSourceType.CI,
                affected_files=[],
                url=_safe_url(item.details_url),
                provenance=identifiers,
            )
        )
    if not items and snapshot.ci.state == CiState.PENDING:
        pending_items = [
            item
            for surface in snapshot.ci_explanation.surfaces
            for item in surface.items
            if item.normalized_state == "pending"
        ]
        if pending_items:
            item = pending_items[0]
            identifiers = sorted({_canonical_ci_item_id(candidate) for candidate in pending_items})
            return [
                ReviewBriefingFocusItem(
                    title=actionable_ci_title(item),
                    description=actionable_ci_description(pending_items),
                    severity="medium",
                    source_type=BriefingSourceType.CI,
                    affected_files=[],
                    url=_safe_url(item.details_url),
                    provenance=identifiers,
                )
            ]
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
    author_described_threads = []
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
        elif thread.lifecycle.attention_state == ReviewConcernAttentionState.AUTHOR_DESCRIBED_CHANGES:
            author_described_threads.append(thread)
    if author_described_threads:
        items.append(_grouped_author_response_focus(author_described_threads))
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


def _grouped_author_response_focus(threads) -> ReviewBriefingFocusItem:
    count = len(threads)
    description = (
        "Author described changes; reviewer verification is still needed."
        if count == 1
        else f"Author described changes in {count} review conversations; reviewer verification is still needed."
    )
    affected_files = sorted({thread.path for thread in threads if thread.path}, key=lambda path: (path.casefold(), path))
    return ReviewBriefingFocusItem(
        title="Verify the author response",
        description=description,
        severity="medium",
        source_type=BriefingSourceType.REVIEW_CONCERN,
        affected_files=affected_files,
        url=_safe_url(threads[0].html_url),
        provenance=sorted({thread.id for thread in threads}),
    )


def _signal_focus(snapshot: PullRequestSnapshot, *, suppress_generic_ci: bool) -> list[ReviewBriefingFocusItem]:
    signals = [
        signal
        for signal in snapshot.signals
        if signal.severity == SignalSeverity.HIGH
        and not (suppress_generic_ci and signal.rule_id == "ci.failing")
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
    canonical_ci_ids: set[str],
) -> list[ReviewBriefingStep]:
    steps: list[ReviewBriefingStep] = []
    seen: set[str] = set()
    focus_thread_ids = {id for item in focus for id in item.provenance if id.startswith("review-thread-")}
    used_paths: set[str] = set()
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
        if item.source_type == BriefingSourceType.FILE_PRIORITY:
            used_paths.update(item.affected_files)
    priority_paths = {file.path for file in priority_files}
    reserved_file_slots = 1 if priority_files else 0
    for action in snapshot.review_actions:
        if _is_generic_ci_action(action) and canonical_ci_ids:
            continue
        if _is_generic_file_review_action(action, priority_paths):
            continue
        if _is_duplicate_review_concern_action(action, focus_thread_ids):
            continue
        if len(steps) >= MAX_STEPS - reserved_file_slots:
            break
        _append_action_step(steps, seen, action, used_paths)
    for file in priority_files:
        if file.path in used_paths:
            continue
        _append_step(
            steps,
            seen,
            title=f"Review {file.path}",
            description=_priority_file_step_description(snapshot, file),
            category="file_priority",
            affected_files=[file.path],
            url=file.url,
            source_ids=[file.path],
        )
        used_paths.add(file.path)
    return [step.model_copy(update={"order": index}) for index, step in enumerate(_dedupe_steps(steps)[:MAX_STEPS], start=1)]


def _append_action_step(steps: list[ReviewBriefingStep], seen: set[str], action: ReviewAction, used_paths: set[str]) -> None:
    url = _url_from_evidence(action.evidence)
    evidence_ids = _review_thread_ids_from_evidence(action.evidence)
    _append_step(
        steps,
        seen,
        title=_imperative_title(action.title),
        description=action.description,
        category=action.category.value,
        affected_files=action.affected_files,
        url=url,
        source_ids=[action.id, action.rule_id, *evidence_ids],
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
    key = _step_key(title, category, source_ids, affected_files)
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
        return f"Blocked by {_sentence_fragment(primary.title.removeprefix('Inspect '))}."
    if snapshot.ci.state == CiState.PENDING:
        count = snapshot.ci.pending_count or snapshot.ci_explanation.pending_count
        return f"Not ready while {count} {_plural(count, 'check is', 'checks are')} pending."
    if status == "ready_with_caution" and primary:
        return f"Ready with caution because {_sentence_fragment(primary.title)}."
    if status == "ready":
        suffix = "currently visible evidence"
        if snapshot.evidence_confidence.score < 100:
            suffix = "the currently visible evidence, with noted evidence limits"
        return f"Ready based on {suffix}."
    if primary:
        return f"{_title_status(status)} because {_sentence_fragment(primary.title)}."
    return f"{_title_status(status)} based on the currently visible evidence."


def _sentence_fragment(value: str) -> str:
    if any(provider in value for provider in ("GitHub Actions", "GitHub", "Vercel", "CircleCI")):
        return value[:1].lower() + value[1:]
    return value.lower()


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
    return [f"[ ] {step.title}" for step in _dedupe_steps(steps)[:MAX_STEPS]]


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
    by_key: dict[str, ReviewBriefingFocusItem] = {}
    for item in sorted(items, key=lambda item: (_source_order(item.source_type), _severity_order(item.severity), item.title, item.affected_files)):
        key = _focus_key(item)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = item
            continue
        by_key[key] = existing.model_copy(
            update={
                "affected_files": sorted({*existing.affected_files, *item.affected_files}, key=lambda path: (path.casefold(), path)),
                "provenance": sorted({*existing.provenance, *item.provenance}),
                "url": existing.url or item.url,
            }
        )
    return list(by_key.values())


def _dedupe_steps(steps: list[ReviewBriefingStep]) -> list[ReviewBriefingStep]:
    deduped: list[ReviewBriefingStep] = []
    seen: set[str] = set()
    for step in steps:
        key = _step_key(step.title, step.category, step.source_ids, step.affected_files)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(step)
    return deduped


def _step_key(title: str, category: str, source_ids: list[str], affected_files: list[str]) -> str:
    if category == "ci":
        ci_ids = sorted(_ci_step_identity(id) for id in source_ids if id.startswith("ci:"))
        if ci_ids:
            return f"ci:{ci_ids[0]}"
        return "ci:generic"
    if category in {"review_concern", "review"}:
        thread_ids = sorted(id for id in source_ids if id.startswith("review-thread-"))
        if thread_ids:
            return f"review_concern:{','.join(thread_ids)}"
    normalized_title = title.casefold().replace("the ", "").replace("author's ", "author ")
    if affected_files:
        return f"{category}:{normalized_title}:paths:{','.join(sorted(set(affected_files)))}"
    return f"{category}:{normalized_title}:{','.join(source_ids)}"


def _is_generic_ci_action(action: ReviewAction) -> bool:
    return action.rule_id == "action.inspect_failing_ci"


def _is_generic_file_review_action(action: ReviewAction, priority_paths: set[str]) -> bool:
    if action.rule_id != "action.review_highest_priority_files":
        return False
    return bool(priority_paths & set(action.affected_files))


def _is_duplicate_review_concern_action(action: ReviewAction, focus_thread_ids: set[str]) -> bool:
    if not action.rule_id.startswith("action.review_concern."):
        return False
    return bool(set(_review_thread_ids_from_evidence(action.evidence)) & focus_thread_ids)


def _file_reason_text(file) -> str:
    return "; ".join(factor.description for factor in file.factors[:2]) or f"{file.level.value} priority changed file."


def _priority_file_step_description(snapshot: PullRequestSnapshot, priority_file: ReviewBriefingPriorityFile) -> str:
    ranked = next((file for file in snapshot.ranked_files if file.path == priority_file.path), None)
    if ranked is None:
        return "; ".join(priority_file.reasons) or f"{priority_file.level} priority changed file."
    parts: list[str] = []
    context_phrase = _file_context_phrase(ranked)
    magnitude = str(ranked.change_magnitude.value).replace("_", " ")
    if magnitude in {"large", "very large"}:
        parts.append(f"{magnitude.title()} {context_phrase} change")
    else:
        parts.append(f"{context_phrase.capitalize()} change")
    if _has_review_conversations(snapshot, ranked.path):
        parts.append("with review conversations")
    if _has_test_gap_signal(snapshot, ranked.related_signal_ids):
        parts.append("and no corresponding test-file change")
    elif ranked.factors:
        parts.append(f"prioritized because {ranked.factors[0].description.rstrip('.').lower()}")
    return " ".join(parts).rstrip(".") + "."


def _file_context_phrase(file) -> str:
    context = file.context
    words: list[str] = []
    if "protected_route_group" in context.access_context:
        words.append("protected")
    if "admin" in context.areas:
        words.append("admin")
    if context.component_role == "route_page":
        words.append("route")
    elif context.is_user_facing:
        words.append("user-facing")
    if not words:
        kind = str(file.primary_kind.value).replace("_", " ")
        words.append(kind)
    return " ".join(words)


def _has_review_conversations(snapshot: PullRequestSnapshot, path: str) -> bool:
    return any(thread.path == path and thread.lifecycle.attention_state != ReviewConcernAttentionState.OUTDATED for thread in snapshot.review_context.threads)


def _has_test_gap_signal(snapshot: PullRequestSnapshot, signal_ids: list[str]) -> bool:
    signal_by_id = {signal.id: signal for signal in snapshot.signals}
    return any(
        signal_by_id[signal_id].rule_id in {"testing.production_change_without_test_files", "testing.sensitive_change_without_test_files"}
        for signal_id in signal_ids
        if signal_id in signal_by_id
    )


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


def _review_thread_ids_from_evidence(evidence: list[str]) -> list[str]:
    ids: list[str] = []
    for item in evidence:
        marker = "Conversation: "
        if item.startswith(marker):
            value = item.removeprefix(marker).strip().rstrip(".")
            if value.startswith("review-thread-"):
                ids.append(value)
    return sorted(set(ids))


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


def _canonical_ci_item_id(item) -> str:
    provider = str(item.provider or "unknown").strip() or "unknown"
    name = str(item.name or provider).strip() or provider
    detail = _safe_url(item.details_url) or ""
    category = str(item.category.value or "unknown")
    return f"ci:{item.source_type.value}:{provider.casefold()}:{category}:{name.casefold()}:{detail}"


def _canonical_ci_concern_key(item) -> str:
    provider = str(item.provider or "unknown").strip().casefold() or "unknown"
    category = str(item.category.value or "unknown").strip().casefold() or "unknown"
    return f"ci:{item.source_type.value}:{provider}:{category}"


def _ci_step_identity(identifier: str) -> str:
    parts = identifier.split(":")
    if len(parts) >= 5:
        return ":".join(parts[:4])
    return identifier


def _focus_key(item: ReviewBriefingFocusItem) -> str:
    if item.source_type == BriefingSourceType.CI:
        ci_ids = sorted(_ci_step_identity(id) for id in item.provenance if id.startswith("ci:"))
        return ci_ids[0] if ci_ids else "ci:generic"
    if item.source_type == BriefingSourceType.FILE_PRIORITY and item.affected_files:
        return f"file:{item.affected_files[0]}"
    if item.source_type == BriefingSourceType.REVIEW_CONCERN:
        if item.title == "Verify the author response":
            return f"review:{item.title.casefold()}:{','.join(sorted(item.affected_files))}"
        thread_ids = sorted(id for id in item.provenance if id.startswith("review-thread-"))
        return f"review:{','.join(thread_ids)}" if thread_ids else f"review:{item.title.casefold()}:{','.join(item.affected_files)}"
    return f"{item.source_type.value}:{item.title.casefold()}:{','.join(sorted(item.affected_files))}"


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
