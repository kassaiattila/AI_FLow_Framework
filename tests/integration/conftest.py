"""Integration-test globals — disable Langfuse cloud flush.

Per-test ``create_app()`` instantiates a fresh ``LangfuseTracer`` whose
shutdown flushes to ``cloud.langfuse.com``. Sequentially creating and
shutting down N clients in one pytest run eventually wedges on a flush
call (observed as the S98 webhook_router sequence-hang). Integration
tests hit real PostgreSQL + Redis but must NOT depend on an external
tracing endpoint.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_langfuse_for_integration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AIFLOW_LANGFUSE__ENABLED", "false")
