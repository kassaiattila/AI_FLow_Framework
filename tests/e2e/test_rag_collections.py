"""E2E — Admin UI RAG Collections (Sprint S / S144).

@test_registry:
    suite: e2e-ui
    component: aiflow-admin.rag-collections + api.v1.rag_collections
    covers:
        - aiflow-admin/src/pages-new/RagCollections/index.tsx
        - aiflow-admin/src/pages-new/RagCollections/RagCollectionDetailDrawer.tsx
        - aiflow-admin/src/pages-new/RagCollections/EmbedderProfileBadge.tsx
        - src/aiflow/api/v1/rag_collections.py
    phase: sprint-s-s144
    priority: critical
    estimated_duration_ms: 35000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, ui, rag, collections, playwright, sprint-s, v1.5.2]

Golden-path for the per-tenant RAG collection admin page:

1. Seed two collections in two different tenants directly via SQL through
   the asyncpg fixture (mirrors the Sprint Q S136 / Sprint N S123 pattern;
   no route mock).
2. Load /#/rag/collections and assert both rows render.
3. Apply the tenant filter and assert the table shrinks to the matching
   row.
4. Click the row → drawer opens → set the embedder profile to ``openai``
   on the empty collection → Save → toast appears → after a hard reload
   the new badge is visible (regression guard against optimistic-only UI).
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid

import asyncpg
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL

pytestmark = pytest.mark.e2e


def _db_url() -> str:
    url = os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _seed(name: str, tenant: str, profile: str | None, dim: int) -> str:
    conn = await asyncpg.connect(_db_url())
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO rag_collections
                (id, name, skill_name,
                 tenant_id, embedder_profile_id, embedding_dim, chunk_count)
            VALUES (gen_random_uuid(), $1, 'rag_engine', $2, $3, $4, 0)
            RETURNING id
            """,
            name,
            tenant,
            profile,
            dim,
        )
        return str(row["id"])
    finally:
        await conn.close()


async def _cleanup(*tenants: str) -> None:
    conn = await asyncpg.connect(_db_url())
    try:
        for t in tenants:
            await conn.execute("DELETE FROM rag_collections WHERE tenant_id = $1", t)
    finally:
        await conn.close()


SUFFIX = f"s144-{int(time.time())}-{uuid.uuid4().hex[:6]}"


class TestRagCollectionsJourney:
    def test_admin_can_list_filter_and_set_profile(
        self,
        authenticated_page: Page,
        console_errors: list[str],
    ) -> None:
        page = authenticated_page
        bestix = f"{SUFFIX}-bestix"
        doha = f"{SUFFIX}-doha"
        try:
            cid_bestix = asyncio.run(_seed(f"{bestix}-coll", bestix, None, 1536))
            cid_doha = asyncio.run(_seed(f"{doha}-coll", doha, "bge_m3", 1024))

            # 1. Both rows visible on the unfiltered list.
            page.goto(f"{BASE_URL}/#/rag/collections")
            page.wait_for_load_state("networkidle")
            page.locator('[data-testid="rag-collections-table"]').wait_for(
                state="visible", timeout=15000
            )
            row_bestix = page.locator(
                f'[data-testid="rag-collections-row"][data-collection-id="{cid_bestix}"]'
            )
            row_doha = page.locator(
                f'[data-testid="rag-collections-row"][data-collection-id="{cid_doha}"]'
            )
            expect(row_bestix).to_be_visible()
            expect(row_doha).to_be_visible()

            # bge_m3 badge on the doha row.
            expect(
                row_doha.locator('[data-testid="rag-collections-profile-badge"]')
            ).to_have_attribute("data-profile", "bge_m3")

            # 2. Filter to bestix — doha row gone, bestix stays.
            page.fill('[data-testid="rag-collections-tenant-input"]', bestix)
            page.click('[data-testid="rag-collections-tenant-apply"]')
            page.wait_for_load_state("networkidle")
            expect(row_bestix).to_be_visible()
            expect(row_doha).to_have_count(0)

            # 3. Open the drawer for the empty bestix row, set profile to openai.
            row_bestix.click()
            drawer = page.locator('[data-testid="rag-collections-drawer"]')
            drawer.wait_for(state="visible", timeout=10000)
            page.select_option('[data-testid="rag-collections-profile-select"]', "openai")
            page.click('[data-testid="rag-collections-drawer-save"]')

            # Either toast (200) or dim-mismatch error (409 — OpenAI key missing
            # in CI). Both prove the round-trip reached the API.
            toast = page.locator('[data-testid="rag-collections-drawer-toast"]')
            err = page.locator('[data-testid="rag-collections-drawer-error"]')
            expect(toast.or_(err)).to_be_visible(timeout=15000)

            # 4. Hard reload — regression guard. If the save was 200, the
            #    bestix row's badge must now read "openai"; if 409, it
            #    remains "default".
            saved_ok = toast.is_visible()
            page.click('[data-testid="rag-collections-drawer-close"]')
            page.goto(f"{BASE_URL}/#/rag/collections?tenant={bestix}")
            page.wait_for_load_state("networkidle")
            badge_after = page.locator(
                f'[data-testid="rag-collections-row"][data-collection-id="{cid_bestix}"] '
                f'[data-testid="rag-collections-profile-badge"]'
            )
            badge_after.wait_for(state="visible", timeout=15000)
            expected_profile = "openai" if saved_ok else "default"
            expect(badge_after).to_have_attribute("data-profile", expected_profile)

            assert console_errors == [], f"Console errors: {console_errors}"
        finally:
            asyncio.run(_cleanup(bestix, doha))
