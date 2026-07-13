#!/usr/bin/env python3
"""Smoke-test a deployed MergeSignal backend without printing response bodies."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 10
SNAPSHOT_FIELDS = {
    "merge_readiness",
    "merge_risk",
    "evidence_confidence",
    "ranked_files",
    "review_actions",
    "review_briefing",
}
REVIEW_BRIEFING_FIELDS = {
    "status",
    "headline",
    "review_focus",
    "priority_files",
    "recommended_steps",
    "checklist",
}


@dataclass(frozen=True)
class SmokeResult:
    ok: bool
    label: str
    detail: str


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        base_url = normalize_base_url(args.backend_base_url)
    except ValueError as error:
        print(f"FAIL backend URL: {error}")
        return 2

    results = [
        check_get(base_url, "/health", "health"),
        check_get(base_url, "/openapi.json", "openapi"),
    ]
    if args.pull_request_url:
        results.append(check_snapshot(base_url, args.pull_request_url, args.timeout))

    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"{status} {result.label}: {result.detail}")

    return 0 if all(result.ok for result in results) else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test a MergeSignal backend deployment.")
    parser.add_argument("backend_base_url", help="Base URL of the backend, for example https://api.example.com")
    parser.add_argument("--pull-request-url", help="Optional public GitHub pull-request URL to snapshot.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Request timeout in seconds.")
    return parser.parse_args(argv)


def normalize_base_url(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("backend base URL is required")
    if not stripped.startswith(("http://", "https://")):
        raise ValueError("backend base URL must use http or https")
    return stripped.rstrip("/") + "/"


def check_get(base_url: str, path: str, label: str) -> SmokeResult:
    payload, error = request_json("GET", urljoin(base_url, path.lstrip("/")))
    if error:
        return SmokeResult(False, label, error)
    if not isinstance(payload, dict):
        return SmokeResult(False, label, "response was not a JSON object")
    return SmokeResult(True, label, "reachable")


def check_snapshot(base_url: str, pull_request_url: str, timeout: float) -> SmokeResult:
    payload, error = request_json(
        "POST",
        urljoin(base_url, "api/v1/pull-requests/snapshot"),
        {"url": pull_request_url},
        timeout=timeout,
    )
    if error:
        return SmokeResult(False, "snapshot", error)
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return SmokeResult(False, "snapshot", "response did not include a data object")

    missing = sorted(SNAPSHOT_FIELDS - set(data))
    if missing:
        return SmokeResult(False, "snapshot", "missing fields: " + ", ".join(missing))

    briefing = data.get("review_briefing")
    if not isinstance(briefing, dict):
        return SmokeResult(False, "snapshot", "review_briefing was not an object")
    missing_briefing = sorted(REVIEW_BRIEFING_FIELDS - set(briefing))
    if missing_briefing:
        return SmokeResult(
            False,
            "snapshot",
            "review_briefing missing fields: " + ", ".join(missing_briefing),
        )
    return SmokeResult(True, "snapshot", "required report fields present")


def request_json(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status < 200 or response.status >= 300:
                return None, f"HTTP {response.status}"
            return json.loads(response.read().decode("utf-8")), None
    except HTTPError as error:
        return None, f"HTTP {error.code}"
    except (OSError, URLError, TimeoutError) as error:
        return None, error.__class__.__name__
    except json.JSONDecodeError:
        return None, "invalid JSON"


if __name__ == "__main__":
    raise SystemExit(main())
