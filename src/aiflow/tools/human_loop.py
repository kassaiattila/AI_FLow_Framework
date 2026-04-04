"""Human loop manager -- operator approval via file signals or API.

Provides a simple file-based signalling mechanism for human-in-the-loop
workflows.  An approval request is written as a JSON file; an operator
(or CLI tool) writes a corresponding response file to approve or reject.

Canonical location: ``aiflow.tools.human_loop``
Backward-compat re-export: ``aiflow.contrib.human_loop``

Flow:
    1. ``request_approval()`` writes ``request_{id}.json`` to *signals_dir*
    2. Logs instructions to console via structlog
    3. Polls for ``approval_{id}.json`` every *poll_interval_seconds*
    4. Returns ``HumanLoopResponse`` when response found or timeout

Usage::

    manager = HumanLoopManager(signals_dir=Path("./signals"))
    response = await manager.request_approval(
        question="Is the extracted table correct?",
        context={"rows": 42, "source": "invoice.pdf"},
        options=["Approve", "Reject", "Edit"],
        timeout_minutes=30,
    )
    if response.approved:
        # proceed
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = [
    "HumanLoopManager",
    "HumanLoopResponse",
    "ApprovalRequest",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ApprovalRequest(BaseModel):
    """A request for human approval or decision."""

    request_id: str
    question: str
    context: dict[str, Any] = Field(default_factory=dict)
    options: list[str] = Field(default_factory=lambda: ["Done", "Skip"])
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    timeout_minutes: int = 60


class HumanLoopResponse(BaseModel):
    """Operator response to an approval request."""

    request_id: str
    approved: bool
    selected_option: str = ""
    operator_notes: str = ""
    responded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class HumanLoopManager:
    """Manage operator approvals via file-based signals.

    The manager writes request files and polls for response files in a
    designated *signals_dir*.  This keeps the mechanism simple, portable,
    and independent of any external service.

    For production deployments the polling can be replaced by an API
    endpoint or message queue without changing the caller interface.
    """

    def __init__(self, signals_dir: Path = Path("./signals")) -> None:
        self.signals_dir = signals_dir
        self.signals_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Request / poll
    # ------------------------------------------------------------------

    async def request_approval(
        self,
        question: str,
        context: dict[str, Any] | None = None,
        options: list[str] | None = None,
        timeout_minutes: int = 60,
        poll_interval_seconds: int = 5,
    ) -> HumanLoopResponse:
        """Request operator approval.  Blocks until response or timeout.

        Parameters
        ----------
        question:
            Human-readable description of what needs approval.
        context:
            Arbitrary context dict shown to the operator.
        options:
            List of possible responses (default ``["Done", "Skip"]``).
        timeout_minutes:
            How long to wait before auto-rejecting.
        poll_interval_seconds:
            How frequently to check for the response file.

        Returns
        -------
        HumanLoopResponse -- ``approved=True`` if the operator selected the
        first option, ``approved=False`` on timeout or explicit rejection.
        """
        request_id = uuid.uuid4().hex[:12]
        effective_options = options or ["Done", "Skip"]

        request = ApprovalRequest(
            request_id=request_id,
            question=question,
            context=context or {},
            options=effective_options,
            timeout_minutes=timeout_minutes,
        )

        # Write request file
        request_path = self.signals_dir / f"request_{request_id}.json"
        request_path.write_text(
            request.model_dump_json(indent=2),
            encoding="utf-8",
        )

        logger.info(
            "human_loop_approval_requested",
            request_id=request_id,
            question=question,
            options=effective_options,
            timeout_minutes=timeout_minutes,
            request_file=str(request_path),
        )
        logger.info(
            "human_loop_instructions",
            msg=(
                f"Operator action required. To approve, create file: "
                f"{self.signals_dir / f'approval_{request_id}.json'} "
                f'with content: {{"approved": true, "selected_option": "<option>", '
                f'"operator_notes": "..."}}'
            ),
        )

        # Poll for response
        response_path = self.signals_dir / f"approval_{request_id}.json"
        deadline_seconds = timeout_minutes * 60
        elapsed = 0.0

        while elapsed < deadline_seconds:
            if response_path.exists():
                try:
                    raw = json.loads(response_path.read_text(encoding="utf-8"))
                    response = HumanLoopResponse(
                        request_id=request_id,
                        approved=raw.get("approved", False),
                        selected_option=raw.get("selected_option", ""),
                        operator_notes=raw.get("operator_notes", ""),
                    )
                    logger.info(
                        "human_loop_response_received",
                        request_id=request_id,
                        approved=response.approved,
                        selected_option=response.selected_option,
                        elapsed_seconds=round(elapsed, 1),
                    )
                    return response
                except (json.JSONDecodeError, Exception) as exc:
                    logger.warning(
                        "human_loop_response_parse_error",
                        request_id=request_id,
                        error=str(exc),
                    )
                    # Continue polling -- file may be partially written

            await asyncio.sleep(poll_interval_seconds)
            elapsed += poll_interval_seconds

        # Timeout
        logger.warning(
            "human_loop_timeout",
            request_id=request_id,
            timeout_minutes=timeout_minutes,
        )
        return HumanLoopResponse(
            request_id=request_id,
            approved=False,
            selected_option="timeout",
            operator_notes=f"Auto-rejected after {timeout_minutes} minute(s) timeout",
        )

    # ------------------------------------------------------------------
    # Manual approval helpers
    # ------------------------------------------------------------------

    def approve_via_file(
        self,
        request_id: str,
        option: str = "Done",
        notes: str = "",
    ) -> None:
        """Write an approval response file (for CLI or scripted use).

        Parameters
        ----------
        request_id:
            The ``request_id`` from the ``ApprovalRequest``.
        option:
            Selected option string.
        notes:
            Optional operator notes.
        """
        response = HumanLoopResponse(
            request_id=request_id,
            approved=True,
            selected_option=option,
            operator_notes=notes,
        )
        response_path = self.signals_dir / f"approval_{request_id}.json"
        response_path.write_text(
            response.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.info(
            "human_loop_approved_via_file",
            request_id=request_id,
            option=option,
            path=str(response_path),
        )

    def approve_via_cli(self, request_id: str) -> HumanLoopResponse:
        """Interactive CLI approval (for development / testing).

        Reads the request file, displays the question and options, then
        prompts the operator via ``input()``.  This is synchronous and
        intended for local dev only.
        """
        request_path = self.signals_dir / f"request_{request_id}.json"
        if not request_path.exists():
            logger.error("human_loop_request_not_found", request_id=request_id)
            return HumanLoopResponse(
                request_id=request_id,
                approved=False,
                selected_option="error",
                operator_notes="Request file not found",
            )

        raw = json.loads(request_path.read_text(encoding="utf-8"))
        question = raw.get("question", "No question provided")
        options = raw.get("options", ["Done", "Skip"])

        print(f"\n{'=' * 60}")
        print(f"  HUMAN APPROVAL REQUIRED  (id: {request_id})")
        print(f"{'=' * 60}")
        print(f"\n  {question}\n")
        for i, opt in enumerate(options, 1):
            print(f"  [{i}] {opt}")
        print()

        choice = input("  Select option number (or 0 to reject): ").strip()
        notes = input("  Notes (optional): ").strip()

        try:
            choice_idx = int(choice)
        except ValueError:
            choice_idx = 0

        if 1 <= choice_idx <= len(options):
            selected = options[choice_idx - 1]
            approved = True
        else:
            selected = "rejected"
            approved = False

        response = HumanLoopResponse(
            request_id=request_id,
            approved=approved,
            selected_option=selected,
            operator_notes=notes,
        )

        # Also write the response file so the polling loop picks it up
        response_path = self.signals_dir / f"approval_{request_id}.json"
        response_path.write_text(
            response.model_dump_json(indent=2),
            encoding="utf-8",
        )

        logger.info(
            "human_loop_approved_via_cli",
            request_id=request_id,
            approved=approved,
            selected_option=selected,
        )
        return response

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def list_pending_requests(self) -> list[ApprovalRequest]:
        """Return all pending (unanswered) approval requests."""
        pending: list[ApprovalRequest] = []
        for req_file in sorted(self.signals_dir.glob("request_*.json")):
            request_id = req_file.stem.replace("request_", "")
            approval_file = self.signals_dir / f"approval_{request_id}.json"
            if not approval_file.exists():
                try:
                    raw = json.loads(req_file.read_text(encoding="utf-8"))
                    pending.append(ApprovalRequest(**raw))
                except Exception as exc:
                    logger.warning(
                        "human_loop_parse_error",
                        file=str(req_file),
                        error=str(exc),
                    )
        return pending

    def cleanup(self, request_id: str) -> None:
        """Remove request and approval files for a completed request."""
        for pattern in (f"request_{request_id}.json", f"approval_{request_id}.json"):
            path = self.signals_dir / pattern
            if path.exists():
                path.unlink()
                logger.debug("human_loop_cleanup", file=str(path))
