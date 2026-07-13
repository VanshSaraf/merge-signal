import json
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3] / "scripts"))

import smoke_deployment  # noqa: E402


def valid_snapshot_payload() -> dict:
    return {
        "data": {
            "merge_readiness": {},
            "merge_risk": {},
            "evidence_confidence": {},
            "ranked_files": [],
            "review_actions": [],
            "review_briefing": {
                "status": "ready",
                "headline": "Ready based on currently visible evidence.",
                "review_focus": [],
                "priority_files": [],
                "recommended_steps": [],
                "checklist": [],
            },
        }
    }


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_smoke_script_passes_health_and_openapi_without_snapshot(monkeypatch, capsys) -> None:
    calls: list[str] = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        return FakeResponse({"ok": True})

    monkeypatch.setattr(smoke_deployment, "urlopen", fake_urlopen)

    exit_code = smoke_deployment.main(["https://backend.example.com"])

    assert exit_code == 0
    assert calls == ["https://backend.example.com/health", "https://backend.example.com/openapi.json"]
    assert "PASS health" in capsys.readouterr().out


def test_smoke_script_validates_snapshot_required_fields(monkeypatch, capsys) -> None:
    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/snapshot"):
            return FakeResponse(valid_snapshot_payload())
        return FakeResponse({"ok": True})

    monkeypatch.setattr(smoke_deployment, "urlopen", fake_urlopen)

    exit_code = smoke_deployment.main([
        "https://backend.example.com/",
        "--pull-request-url",
        "https://github.com/octocat/Hello-World/pull/42",
    ])

    assert exit_code == 0
    assert "PASS snapshot" in capsys.readouterr().out


def test_smoke_script_fails_when_review_briefing_is_missing(monkeypatch, capsys) -> None:
    payload = valid_snapshot_payload()
    del payload["data"]["review_briefing"]

    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/snapshot"):
            return FakeResponse(payload)
        return FakeResponse({"ok": True})

    monkeypatch.setattr(smoke_deployment, "urlopen", fake_urlopen)

    exit_code = smoke_deployment.main([
        "https://backend.example.com",
        "--pull-request-url",
        "https://github.com/example-owner/example-repo/pull/42",
    ])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "missing fields: review_briefing" in output


def test_smoke_script_fails_when_review_briefing_is_not_an_object(monkeypatch, capsys) -> None:
    payload = valid_snapshot_payload()
    payload["data"]["review_briefing"] = []

    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/snapshot"):
            return FakeResponse(payload)
        return FakeResponse({"ok": True})

    monkeypatch.setattr(smoke_deployment, "urlopen", fake_urlopen)

    exit_code = smoke_deployment.main([
        "https://backend.example.com",
        "--pull-request-url",
        "https://github.com/example-owner/example-repo/pull/42",
    ])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "review_briefing was not an object" in output


def test_smoke_script_fails_when_review_briefing_field_is_missing(monkeypatch, capsys) -> None:
    payload = valid_snapshot_payload()
    del payload["data"]["review_briefing"]["checklist"]

    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/snapshot"):
            return FakeResponse(payload)
        return FakeResponse({"ok": True})

    monkeypatch.setattr(smoke_deployment, "urlopen", fake_urlopen)

    exit_code = smoke_deployment.main([
        "https://backend.example.com",
        "--pull-request-url",
        "https://github.com/example-owner/example-repo/pull/42",
    ])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "review_briefing missing fields: checklist" in output


def test_smoke_script_fails_without_dumping_response_body(monkeypatch, capsys) -> None:
    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/snapshot"):
            return FakeResponse({"data": {"merge_readiness": {}, "secret": "do-not-print"}})
        return FakeResponse({"ok": True})

    monkeypatch.setattr(smoke_deployment, "urlopen", fake_urlopen)

    exit_code = smoke_deployment.main([
        "https://backend.example.com",
        "--pull-request-url",
        "https://github.com/octocat/Hello-World/pull/42",
    ])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL snapshot" in output
    assert "do-not-print" not in output


@pytest.mark.parametrize("value", ["", "backend.example.com", "ftp://backend.example.com"])
def test_smoke_script_rejects_invalid_backend_url(value: str, capsys) -> None:
    exit_code = smoke_deployment.main([value])

    assert exit_code == 2
    assert "FAIL backend URL" in capsys.readouterr().out
