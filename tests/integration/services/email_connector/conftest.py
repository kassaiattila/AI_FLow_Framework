"""Per-test pool reset — avoid the asyncpg pool + event loop trap.

pytest-asyncio creates a fresh event loop per ``@pytest.mark.asyncio``
function. The module-level ``aiflow.api.deps.get_pool()`` caches an
``asyncpg.Pool`` bound to the loop of the first caller, so the second
test reuses a pool whose connections live on a closed loop → the
``InterfaceError: another operation is in progress`` failure we saw
when ``test_scan_and_classify.py`` and ``test_intent_routing.py`` ran
back-to-back. See ``feedback_asyncpg_pool_event_loop.md``.
"""

from __future__ import annotations

import pytest

from aiflow.api import deps


@pytest.fixture(autouse=True)
async def _reset_deps_pool() -> None:
    """Close cached pool/engine after each test so the next loop is clean."""
    yield
    await deps.close_all()
