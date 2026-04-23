"""Unit tests for aiflow.tools.human_loop — coverage uplift (issue #7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aiflow.tools.human_loop import ApprovalRequest, HumanLoopManager, HumanLoopResponse


def test_approval_request_defaults() -> None:
    req = ApprovalRequest(request_id="abc", question="proceed?")
    assert req.options == ["Done", "Skip"]
    assert req.context == {}
    assert req.timeout_minutes == 60


def test_human_loop_response_defaults() -> None:
    resp = HumanLoopResponse(request_id="abc", approved=True)
    assert resp.approved is True
    assert resp.selected_option == ""
    assert resp.operator_notes == ""


def test_manager_creates_signals_dir(tmp_path: Path) -> None:
    sig = tmp_path / "signals"
    assert not sig.exists()
    HumanLoopManager(signals_dir=sig)
    assert sig.exists() and sig.is_dir()


def test_approve_via_file_writes_response(tmp_path: Path) -> None:
    sig = tmp_path / "signals"
    mgr = HumanLoopManager(signals_dir=sig)
    mgr.approve_via_file("req-1", option="Done", notes="looks good")
    path = sig / "approval_req-1.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["approved"] is True
    assert data["selected_option"] == "Done"
    assert data["operator_notes"] == "looks good"
    assert data["request_id"] == "req-1"


def test_list_pending_requests_empty(tmp_path: Path) -> None:
    mgr = HumanLoopManager(signals_dir=tmp_path / "s")
    assert mgr.list_pending_requests() == []


def test_list_pending_requests_ignores_answered(tmp_path: Path) -> None:
    sig = tmp_path / "s"
    mgr = HumanLoopManager(signals_dir=sig)
    (sig / "request_a.json").write_text(
        json.dumps(
            {
                "request_id": "a",
                "question": "q1",
                "context": {},
                "options": ["Done"],
                "created_at": "2026-01-01T00:00:00+00:00",
                "timeout_minutes": 10,
            }
        ),
        encoding="utf-8",
    )
    (sig / "request_b.json").write_text(
        json.dumps(
            {
                "request_id": "b",
                "question": "q2",
                "context": {},
                "options": ["Done"],
                "created_at": "2026-01-01T00:00:00+00:00",
                "timeout_minutes": 10,
            }
        ),
        encoding="utf-8",
    )
    (sig / "approval_b.json").write_text('{"approved": true}', encoding="utf-8")
    pending = mgr.list_pending_requests()
    assert [p.request_id for p in pending] == ["a"]


def test_list_pending_requests_skips_broken_json(tmp_path: Path) -> None:
    sig = tmp_path / "s"
    mgr = HumanLoopManager(signals_dir=sig)
    (sig / "request_x.json").write_text("not json at all", encoding="utf-8")
    assert mgr.list_pending_requests() == []  # parse error swallowed


def test_cleanup_removes_files(tmp_path: Path) -> None:
    sig = tmp_path / "s"
    mgr = HumanLoopManager(signals_dir=sig)
    (sig / "request_r.json").write_text("{}", encoding="utf-8")
    (sig / "approval_r.json").write_text("{}", encoding="utf-8")
    mgr.cleanup("r")
    assert not (sig / "request_r.json").exists()
    assert not (sig / "approval_r.json").exists()


def test_cleanup_missing_is_noop(tmp_path: Path) -> None:
    mgr = HumanLoopManager(signals_dir=tmp_path / "s")
    mgr.cleanup("does-not-exist")  # no raise


@pytest.mark.asyncio
async def test_request_approval_picks_up_existing_response(tmp_path: Path) -> None:
    """If a response file exists before polling starts, first poll should return it."""
    sig = tmp_path / "s"
    mgr = HumanLoopManager(signals_dir=sig)

    # Pre-populate an approval file BEFORE calling request_approval is impossible
    # because request_id is random. Instead, use poll_interval=0 and race:
    # drop the approval file after request is written. We simulate by writing
    # a matching approval file mid-flight using an asyncio task.
    import asyncio

    async def drop_approval_when_ready() -> None:
        # Poll for request_*.json to appear, then write approval_*.json
        for _ in range(50):
            reqs = list(sig.glob("request_*.json"))
            if reqs:
                rid = reqs[0].stem.replace("request_", "")
                (sig / f"approval_{rid}.json").write_text(
                    json.dumps(
                        {
                            "approved": True,
                            "selected_option": "Done",
                            "operator_notes": "auto",
                        }
                    ),
                    encoding="utf-8",
                )
                return
            await asyncio.sleep(0.01)

    writer = asyncio.create_task(drop_approval_when_ready())
    resp = await mgr.request_approval(
        question="ok?",
        timeout_minutes=1,
        poll_interval_seconds=1,
    )
    await writer
    assert resp.approved is True
    assert resp.selected_option == "Done"


@pytest.mark.asyncio
async def test_request_approval_timeout_rejects(tmp_path: Path) -> None:
    """With timeout_minutes=0 the loop exits without response → approved=False."""
    mgr = HumanLoopManager(signals_dir=tmp_path / "s")
    resp = await mgr.request_approval(
        question="ok?",
        timeout_minutes=0,
        poll_interval_seconds=1,
    )
    assert resp.approved is False
    assert resp.selected_option == "timeout"


@pytest.mark.asyncio
async def test_request_approval_skips_bad_json_then_times_out(tmp_path: Path) -> None:
    """Malformed response file is swallowed; loop continues until timeout."""
    import asyncio

    sig = tmp_path / "s"
    mgr = HumanLoopManager(signals_dir=sig)

    async def drop_bad() -> None:
        for _ in range(50):
            reqs = list(sig.glob("request_*.json"))
            if reqs:
                rid = reqs[0].stem.replace("request_", "")
                (sig / f"approval_{rid}.json").write_text("not json", encoding="utf-8")
                return
            await asyncio.sleep(0.01)

    writer = asyncio.create_task(drop_bad())
    resp = await mgr.request_approval(
        question="ok?",
        timeout_minutes=0,
        poll_interval_seconds=1,
    )
    await writer
    assert resp.approved is False


def test_approve_via_cli_missing_request_returns_error(tmp_path: Path) -> None:
    mgr = HumanLoopManager(signals_dir=tmp_path / "s")
    resp = mgr.approve_via_cli("missing-id")
    assert resp.approved is False
    assert resp.selected_option == "error"
