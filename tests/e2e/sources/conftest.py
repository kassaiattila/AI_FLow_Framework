"""Per-test asyncpg pool reset for source-adapter E2E tests.

pytest-asyncio defaults to function-scoped event loops, but
:func:`aiflow.api.deps.get_pool` caches the pool in a module-global. The
first test creates a pool bound to its own loop; the second test runs on a
fresh loop and re-uses the dead pool, surfacing
``asyncpg.InterfaceError: pool is closed`` (or similar). See
``feedback_asyncpg_pool_event_loop.md``.

The autouse fixture here clears ``_deps._pool`` before AND after each test
so every test in this directory gets a fresh pool on the current loop.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from aiflow.api import deps as _deps


@pytest.fixture(autouse=True)
def _reset_db_pool() -> Iterator[None]:
    _deps._pool = None
    yield
    _deps._pool = None
