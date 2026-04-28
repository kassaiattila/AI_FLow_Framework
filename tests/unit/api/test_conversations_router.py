"""
@test_registry:
    suite: api-unit
    component: api.v1.conversations
    covers:
        - src/aiflow/api/v1/conversations.py
    phase: v1.8.0
    priority: critical
    estimated_duration_ms: 250
    requires_services: []
    tags: [unit, api, conversations, sprint_x, sx_4]
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from aiflow.security.auth import AuthProvider
from aiflow.services.conversations.schemas import (
    Citation,
    ConversationDetail,
    ConversationSummary,
    TurnDetail,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@contextmanager
def _client_and_headers(tenant_id: str = "default"):
    auth = AuthProvider.from_env()
    with patch.object(AuthProvider, "from_env", return_value=auth):
        from aiflow.api.app import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        client.get("/health/live")
        token = auth.create_token(user_id=tenant_id, role="admin")
        yield client, {"Authorization": f"Bearer {token}"}


def _summary(**overrides) -> ConversationSummary:
    base = dict(
        id=uuid.uuid4(),
        tenant_id="default",
        created_by="user-1",
        persona="baseline",
        collection_name="azhu-test",
        title=None,
        created_at=datetime(2026, 4, 28, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 28, 10, 0, tzinfo=UTC),
    )
    base.update(overrides)
    return ConversationSummary(**base)


def _detail(*, turns: list[TurnDetail] | None = None, **overrides) -> ConversationDetail:
    summary = _summary(**overrides)
    return ConversationDetail(**summary.model_dump(), turns=turns or [])


def _turn(**overrides) -> TurnDetail:
    base = dict(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        turn_index=0,
        role="user",
        content="Mi a panaszkezelési hatarido?",
        citations=None,
        cost_usd=None,
        latency_ms=None,
        created_at=datetime(2026, 4, 28, 10, 0, tzinfo=UTC),
    )
    base.update(overrides)
    return TurnDetail(**base)


def _patch_service(
    *,
    list_return=None,
    create_return=None,
    get_return=None,
    append_return=None,
    append_raises: Exception | None = None,
):
    fake = MagicMock()
    fake.list = AsyncMock(return_value=list_return or [])
    fake.create = AsyncMock(return_value=create_return or _summary())
    fake.get = AsyncMock(return_value=get_return)
    if append_raises is not None:
        fake.append_turn = AsyncMock(side_effect=append_raises)
    else:
        fake.append_turn = AsyncMock(return_value=append_return)
    return fake


# ---------------------------------------------------------------------------
# 1. test_post_create_returns_201_with_detail
# ---------------------------------------------------------------------------


class TestCreate:
    def test_post_create_returns_201_with_detail(self):
        created = _summary(persona="expert", collection_name="azhu-test")
        service = _patch_service(create_return=created)
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.conversations._service",
                AsyncMock(return_value=service),
            ),
        ):
            r = client.post(
                "/api/v1/conversations/",
                headers=headers,
                json={"persona": "expert", "collection_name": "azhu-test"},
            )
            assert r.status_code == 201, r.text
            payload = r.json()
            assert payload["persona"] == "expert"
            assert payload["collection_name"] == "azhu-test"
            assert payload["id"] == str(created.id)


# ---------------------------------------------------------------------------
# 2. test_get_list_returns_200_with_default_pagination
# ---------------------------------------------------------------------------


class TestList:
    def test_get_list_returns_200_with_default_pagination(self):
        rows = [_summary(), _summary()]
        service = _patch_service(list_return=rows)
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.conversations._service",
                AsyncMock(return_value=service),
            ),
        ):
            r = client.get("/api/v1/conversations/", headers=headers)
            assert r.status_code == 200, r.text
            assert len(r.json()) == 2
            _args, kwargs = service.list.call_args
            assert kwargs["limit"] == 50
            assert kwargs["offset"] == 0
            assert kwargs["tenant_id"] == "default"

    # -----------------------------------------------------------------
    # 3. test_get_list_rejects_limit_over_200_with_422
    # -----------------------------------------------------------------

    def test_get_list_rejects_limit_over_200_with_422(self):
        service = _patch_service(list_return=[])
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.conversations._service",
                AsyncMock(return_value=service),
            ),
        ):
            r = client.get("/api/v1/conversations/?limit=500", headers=headers)
            assert r.status_code == 422


# ---------------------------------------------------------------------------
# 4. test_get_detail_returns_404_for_missing_id
# ---------------------------------------------------------------------------


class TestDetail:
    def test_get_detail_returns_404_for_missing_id(self):
        service = _patch_service(get_return=None)
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.conversations._service",
                AsyncMock(return_value=service),
            ),
        ):
            missing = uuid.uuid4()
            r = client.get(f"/api/v1/conversations/{missing}", headers=headers)
            assert r.status_code == 404


# ---------------------------------------------------------------------------
# 5. test_post_turns_appends_with_citations
# ---------------------------------------------------------------------------


class TestAppendTurn:
    def test_post_turns_appends_with_citations(self):
        conversation_id = uuid.uuid4()
        appended = _turn(
            conversation_id=conversation_id,
            turn_index=1,
            role="assistant",
            content="A panaszkezelési hatarido 30 nap.",
            citations=[
                Citation(source_id="doc-1", title="ASZF", snippet="...", score=0.91),
            ],
            cost_usd=0.0042,
            latency_ms=312,
        )
        service = _patch_service(append_return=appended)
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.conversations._service",
                AsyncMock(return_value=service),
            ),
        ):
            r = client.post(
                f"/api/v1/conversations/{conversation_id}/turns",
                headers=headers,
                json={
                    "role": "assistant",
                    "content": "A panaszkezelési hatarido 30 nap.",
                    "citations": [
                        {
                            "source_id": "doc-1",
                            "title": "ASZF",
                            "snippet": "...",
                            "score": 0.91,
                        }
                    ],
                    "cost_usd": 0.0042,
                    "latency_ms": 312,
                },
            )
            assert r.status_code == 201, r.text
            payload = r.json()
            assert payload["role"] == "assistant"
            assert payload["turn_index"] == 1
            assert len(payload["citations"]) == 1
            assert payload["cost_usd"] == 0.0042

    # -----------------------------------------------------------------
    # 6. test_post_turns_enforces_tenant_scope
    # -----------------------------------------------------------------

    def test_post_turns_enforces_tenant_scope(self):
        conversation_id = uuid.uuid4()
        # Service returns None when the parent conversation cannot be
        # found under the requested tenant. Router maps that to 404.
        service = _patch_service(append_return=None)
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.conversations._service",
                AsyncMock(return_value=service),
            ),
        ):
            r = client.post(
                f"/api/v1/conversations/{conversation_id}/turns?tenant_id=other-tenant",
                headers=headers,
                json={"role": "user", "content": "kerdes"},
            )
            assert r.status_code == 404
            _args, kwargs = service.append_turn.call_args
            assert kwargs["tenant_id"] == "other-tenant"
