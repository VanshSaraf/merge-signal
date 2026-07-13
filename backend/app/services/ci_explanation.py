from urllib.parse import urlparse

from app.domain.pull_request import (
    CheckRunRecord,
    CiExplanation,
    CiExplanationItem,
    CiState,
    CiSurfaceCategory,
    CiSurfaceSummary,
    CiSurfaceType,
    CommitStatusRecord,
    PullRequestCi,
)


CHECK_FAILURE_CONCLUSIONS = {"failure", "timed_out", "cancelled", "action_required", "startup_failure", "stale"}
CHECK_PENDING_STATUSES = {"queued", "in_progress", "waiting", "requested", "pending"}
STATUS_FAILURE_STATES = {"failure", "error"}
STATUS_PENDING_STATES = {"pending"}


def build_ci_explanation(ci: PullRequestCi) -> CiExplanation:
    items = _deduplicate_items([
        *(_item_from_check_run(run) for run in ci.check_runs),
        *(_item_from_commit_status(status) for status in ci.commit_statuses),
    ])
    items = sorted(items, key=_item_sort_key)
    blocking_items = [item for item in items if item.is_blocking]
    surfaces = _build_surfaces(items)

    return CiExplanation(
        overall_state=ci.state,
        visibility=ci.visibility,
        summary=_summary(ci, items, blocking_items),
        total_count=len(items),
        passing_count=sum(1 for item in items if item.normalized_state == "passing"),
        failing_count=sum(1 for item in items if item.normalized_state == "failing"),
        pending_count=sum(1 for item in items if item.normalized_state == "pending"),
        neutral_count=sum(1 for item in items if item.normalized_state == "neutral"),
        skipped_count=sum(1 for item in items if item.normalized_state == "skipped"),
        unknown_count=sum(1 for item in items if item.normalized_state == "unknown"),
        surfaces=surfaces,
        blocking_items=blocking_items,
        warnings=list(ci.warnings),
    )


def primary_blocker_phrase(explanation: CiExplanation | None) -> str | None:
    if not explanation or not explanation.blocking_items:
        return None
    item = explanation.blocking_items[0]
    category = ci_category_display_label(item.category)
    provider = ci_provider_display_name(item.provider if item.provider and item.provider != item.name else item.name)
    return f"a failed {provider} {category} check"


def actionable_ci_title(item: CiExplanationItem | None, *, state: str | None = None) -> str:
    normalized_state = (state or item.normalized_state if item else state or "").strip().casefold()
    action = "pending" if normalized_state == "pending" else "failed" if normalized_state == "failing" else normalized_state
    if action not in {"failed", "pending"}:
        action = "CI"
    if item is None:
        return "Inspect failed CI check" if action == "failed" else "Inspect pending CI check" if action == "pending" else "Inspect CI check"
    provider = ci_provider_display_name(item.provider)
    category = ci_category_display_label(item.category)
    if provider == "Unknown provider":
        return f"Inspect {action} CI check"
    if category == "unknown":
        return f"Inspect {action} {provider} check"
    return f"Inspect {action} {provider} {category} check"


def actionable_ci_description(items: list[CiExplanationItem]) -> str:
    if not items:
        return "Review the observable CI state for the current head SHA."
    descriptions = sorted({item.description.strip() for item in items if item.description and item.description.strip()})
    if len(items) == 1:
        item = items[0]
        if descriptions:
            return descriptions[0].rstrip(".") + "."
        state = "pending" if item.normalized_state == "pending" else "failing" if item.normalized_state == "failing" else item.normalized_state
        return f"{item.name} is currently {state}."
    category = ci_category_display_label(items[0].category)
    state = "pending" if items[0].normalized_state == "pending" else "failing" if items[0].normalized_state == "failing" else items[0].normalized_state
    category_prefix = "" if category == "unknown" else f"{category} "
    return f"{len(items)} {category_prefix}{_plural('check', len(items))} require review while {state}."


def ci_provider_display_name(value: str | None) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return "Unknown provider"
    lower = normalized.casefold().replace("_", " ").replace("-", " ")
    known = {
        "github": "GitHub",
        "github actions": "GitHub Actions",
        "github checks": "GitHub Checks",
        "vercel": "Vercel",
        "circleci": "CircleCI",
        "circle ci": "CircleCI",
    }
    return known.get(lower, " ".join(word.upper() if word in {"ci", "api"} else word.capitalize() for word in lower.split()))


def ci_category_display_label(category: CiSurfaceCategory | str | None) -> str:
    value = category.value if isinstance(category, CiSurfaceCategory) else str(category or "unknown")
    labels = {
        "authorization_or_configuration": "authorization/configuration",
        "typecheck": "typecheck",
    }
    return labels.get(value, value.replace("_", " "))


def _item_from_check_run(run: CheckRunRecord) -> CiExplanationItem:
    state = _normalize_check_run_state(run)
    provider = run.provider_name or run.provider_slug or "GitHub Checks"
    text = " ".join([run.name, provider, run.provider_slug or ""])
    return CiExplanationItem(
        name=run.name,
        provider=provider,
        source_type=CiSurfaceType.CHECK_RUN,
        normalized_state=state,
        category=_categorize(text),
        description=run.conclusion or run.status,
        details_url=_safe_url(run.details_url),
        is_blocking=state == "failing",
    )


def _item_from_commit_status(status: CommitStatusRecord) -> CiExplanationItem:
    provider = _status_provider(status)
    text = " ".join([status.context, provider, status.creator_login or "", status.description or ""])
    return CiExplanationItem(
        name=status.context,
        provider=provider,
        source_type=CiSurfaceType.COMMIT_STATUS,
        normalized_state=_normalize_status_state(status),
        category=_categorize(text),
        description=status.description,
        details_url=_safe_url(status.target_url),
        is_blocking=status.state.lower() in STATUS_FAILURE_STATES,
    )


def _normalize_check_run_state(run: CheckRunRecord) -> str:
    status = run.status.lower()
    conclusion = run.conclusion.lower() if run.conclusion else None
    if status != "completed" or conclusion is None:
        return "pending" if status in CHECK_PENDING_STATUSES else "unknown"
    if conclusion == "success":
        return "passing"
    if conclusion == "neutral":
        return "neutral"
    if conclusion == "skipped":
        return "skipped"
    if conclusion in CHECK_FAILURE_CONCLUSIONS:
        return "failing"
    return "unknown"


def _normalize_status_state(status: CommitStatusRecord) -> str:
    state = status.state.lower()
    if state == "success":
        return "passing"
    if state in STATUS_FAILURE_STATES:
        return "failing"
    if state in STATUS_PENDING_STATES:
        return "pending"
    return "unknown"


def _status_provider(status: CommitStatusRecord) -> str:
    candidates = [status.context, status.creator_login or ""]
    if any("vercel" in candidate.casefold() for candidate in candidates):
        return "Vercel"
    if status.creator_login:
        return status.creator_login
    return status.context or "Commit status"


def _categorize(text: str) -> CiSurfaceCategory:
    normalized = text.casefold()
    if any(token in normalized for token in ("authorization required", "unauthorized", "forbidden", "permission", "access denied", "configuration required")):
        return CiSurfaceCategory.AUTHORIZATION_OR_CONFIGURATION
    if any(token in normalized for token in ("security", "sast", "dependency review", "codeql", "secret scan")):
        return CiSurfaceCategory.SECURITY
    if any(token in normalized for token in ("typecheck", "type check", "type-check", "tsc")):
        return CiSurfaceCategory.TYPECHECK
    if any(token in normalized for token in ("lint", "eslint", "ruff", "flake8")):
        return CiSurfaceCategory.LINT
    if any(token in normalized for token in ("test", "unit", "e2e", "end-to-end", "integration", "spec")):
        return CiSurfaceCategory.TEST
    if any(token in normalized for token in ("vercel", "deploy", "deployment", "preview")):
        return CiSurfaceCategory.DEPLOYMENT
    if any(token in normalized for token in ("build", "compile", "bundle")):
        return CiSurfaceCategory.BUILD
    if any(token in normalized for token in ("quality", "coverage", "sonar")):
        return CiSurfaceCategory.QUALITY
    return CiSurfaceCategory.UNKNOWN


def _safe_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        return None
    return value


def _deduplicate_items(items: list[CiExplanationItem]) -> list[CiExplanationItem]:
    seen: set[tuple[str, str, str, str | None]] = set()
    deduped: list[CiExplanationItem] = []
    for item in items:
        key = (
            item.source_type.value,
            item.provider.casefold(),
            item.name.casefold(),
            item.details_url,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _build_surfaces(items: list[CiExplanationItem]) -> list[CiSurfaceSummary]:
    grouped: dict[tuple[str, CiSurfaceType], list[CiExplanationItem]] = {}
    for item in items:
        grouped.setdefault((item.provider, item.source_type), []).append(item)
    surfaces: list[CiSurfaceSummary] = []
    for (provider, source_type), surface_items in sorted(grouped.items(), key=lambda item: (item[0][0].casefold(), item[0][1].value)):
        surfaces.append(
            CiSurfaceSummary(
                provider=provider,
                source_type=source_type,
                total_count=len(surface_items),
                passing_count=sum(1 for item in surface_items if item.normalized_state == "passing"),
                failing_count=sum(1 for item in surface_items if item.normalized_state == "failing"),
                pending_count=sum(1 for item in surface_items if item.normalized_state == "pending"),
                neutral_count=sum(1 for item in surface_items if item.normalized_state == "neutral"),
                skipped_count=sum(1 for item in surface_items if item.normalized_state == "skipped"),
                unknown_count=sum(1 for item in surface_items if item.normalized_state == "unknown"),
                items=surface_items,
            )
        )
    return surfaces


def _summary(ci: PullRequestCi, items: list[CiExplanationItem], blocking_items: list[CiExplanationItem]) -> str:
    if not items:
        if ci.visibility.value == "unavailable":
            return "CI surfaces were unavailable for the current head SHA."
        return "No CI checks were visible for the current head SHA."
    passing_count = sum(1 for item in items if item.normalized_state == "passing")
    pending_count = sum(1 for item in items if item.normalized_state == "pending")
    neutral_or_skipped_count = sum(1 for item in items if item.normalized_state in {"neutral", "skipped"})
    parts: list[str] = []
    if passing_count == len(items) and ci.visibility.value == "complete":
        return f"All {passing_count} visible CI { _plural('check', passing_count) } passed."
    if pending_count == len(items):
        return f"{pending_count} { _plural('check', pending_count) } { _is_are(pending_count) } still pending."
    if blocking_items:
        category = ci_category_display_label(blocking_items[0].category)
        provider = ci_provider_display_name(blocking_items[0].provider)
        parts.append(f"{len(blocking_items)} {category} { _plural('check', len(blocking_items)) } { _is_are(len(blocking_items)) } failing on {provider}")
    if passing_count:
        parts.append(f"{passing_count} { _plural('check', passing_count) } passed")
    if pending_count:
        parts.append(f"{pending_count} { _plural('check', pending_count) } pending")
    if neutral_or_skipped_count:
        parts.append(f"{neutral_or_skipped_count} neutral or skipped { _plural('check', neutral_or_skipped_count) }")
    if ci.visibility.value != "complete":
        parts.append(f"visibility is {ci.visibility.value}")
    return _upper_first("; ".join(parts)) + "."


def _category_label(category: CiSurfaceCategory) -> str:
    return ci_category_display_label(category)


def _plural(word: str, count: int) -> str:
    return word if count == 1 else f"{word}s"


def _is_are(count: int) -> str:
    return "is" if count == 1 else "are"


def _upper_first(value: str) -> str:
    return value[:1].upper() + value[1:] if value else value


def _item_sort_key(item: CiExplanationItem) -> tuple[int, str, str, str]:
    state_order = {"failing": 0, "pending": 1, "unknown": 2, "passing": 3, "neutral": 4, "skipped": 5}
    return (state_order.get(item.normalized_state, 6), item.provider.casefold(), item.name.casefold(), item.source_type.value)
