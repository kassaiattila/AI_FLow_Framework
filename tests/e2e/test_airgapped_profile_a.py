"""Air-gapped Profile A smoke: Langfuse self-host + BGE-M3 with no external DNS.

Proves the Sprint M S118 deliverable: the full tracing + Profile A embedding
path works without reaching any host outside localhost / the docker bridge.
The test only runs when the self-hosted Langfuse stack is up (see
``docker-compose.langfuse.yml``) and skips gracefully otherwise, so it can
live in the default `tests/e2e/` collection without blocking CI on
environments without the compose overlay.

Mechanism:
1. Monkeypatch ``socket.getaddrinfo`` to fail loudly on every non-local host.
2. Instantiate ``LangfuseTracer`` against ``http://localhost:3000`` and drive a
   real trace/span/finish/flush cycle through the Langfuse v4 SDK.
3. Poll ``/api/public/traces`` with HTTP basic auth (public/secret keypair from
   ``langfuse#public_key`` + ``langfuse#secret_key`` via the S117 resolver, or
   the legacy env aliases as fallback) and confirm the trace we just emitted
   is visible to the local server.
4. Lazily instantiate ``BGEM3Embedder`` (Profile A) and encode two short
   strings, asserting a non-zero cosine similarity. The BGE-M3 weight download
   is ~2 GB; this step is skipped unless ``AIFLOW_BGE_M3_WEIGHTS_READY=1`` or
   ``sentence_transformers`` + a cached model resolve offline.

@test_registry:
    suite: e2e-airgap
    component: observability.tracing + providers.embedder.bge_m3
    covers:
      - docker-compose.langfuse.yml
      - src/aiflow/observability/tracing.py
      - src/aiflow/providers/embedder/bge_m3.py
    phase: 8
    priority: high
    estimated_duration_ms: 60000
    requires_services: [langfuse, vault]
    tags: [e2e, airgap, langfuse, profile-a, s118]
"""

from __future__ import annotations

import asyncio
import os
import socket
import time
from collections.abc import Iterator

import pytest

# Hard dep gate: if the langfuse SDK is absent, nothing below is reachable.
pytest.importorskip("langfuse", reason="langfuse SDK required for S118 air-gap E2E")

import httpx

from aiflow.observability.tracing import LangfuseTracer

LANGFUSE_HOST = os.getenv("AIFLOW_LANGFUSE__HOST", "http://localhost:3000").rstrip("/")
_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", "host.docker.internal"}


def _langfuse_is_up() -> bool:
    try:
        resp = httpx.get(f"{LANGFUSE_HOST}/api/public/health", timeout=3.0)
        return resp.status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(
    not _langfuse_is_up(),
    reason=(
        f"self-hosted Langfuse not reachable at {LANGFUSE_HOST}; "
        "bring up the stack via `docker compose -f docker-compose.langfuse.yml up -d`"
    ),
)


def _resolve_keypair() -> tuple[str, str] | None:
    """Pull public/secret from the S117 resolver, fall back to env aliases."""
    try:
        from aiflow.security.resolver import get_secret_manager

        mgr = get_secret_manager()
        pk = mgr.get_secret("langfuse#public_key", env_alias="AIFLOW_LANGFUSE__PUBLIC_KEY") or ""
        sk = mgr.get_secret("langfuse#secret_key", env_alias="AIFLOW_LANGFUSE__SECRET_KEY") or ""
    except Exception:
        pk = os.getenv("AIFLOW_LANGFUSE__PUBLIC_KEY", "")
        sk = os.getenv("AIFLOW_LANGFUSE__SECRET_KEY", "")
    return (pk, sk) if pk and sk else None


@pytest.fixture
def airgap_guard(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Block every non-local hostname at the socket layer.

    The matching rule is deliberately strict: no wildcard subdomain of
    ``.langfuse.com`` / ``.openai.com`` / ``.anthropic.com`` can sneak through
    because only hosts that appear in ``_ALLOWED_HOSTS`` (or end in
    ``.localhost``) resolve. Everything else raises ``RuntimeError``, which
    surfaces in the failing test with the offending hostname attached.
    """
    original = socket.getaddrinfo

    def guarded(host, *args, **kwargs):  # type: ignore[no-untyped-def]
        if host is None:
            return original(host, *args, **kwargs)
        hostname = str(host)
        if hostname in _ALLOWED_HOSTS or hostname.endswith(".localhost"):
            return original(host, *args, **kwargs)
        raise RuntimeError(f"air-gap violation: getaddrinfo({hostname!r})")

    monkeypatch.setattr(socket, "getaddrinfo", guarded)
    yield


def _poll_trace(public_key: str, secret_key: str, name: str, timeout_s: float = 15.0) -> bool:
    """Poll the Langfuse REST surface until the just-emitted trace shows up."""
    deadline = time.monotonic() + timeout_s
    auth = (public_key, secret_key)
    while time.monotonic() < deadline:
        resp = httpx.get(
            f"{LANGFUSE_HOST}/api/public/traces",
            params={"limit": 20},
            auth=auth,
            timeout=5.0,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            if any(t.get("name") == name for t in data):
                return True
        time.sleep(0.5)
    return False


class TestAirgappedProfileA:
    """S118 — self-hosted Langfuse + Profile A embedder under DNS lockdown."""

    def test_tracer_round_trip_under_airgap(self, airgap_guard: None) -> None:
        """Full trace/span lifecycle lands in the self-hosted Langfuse."""
        keys = _resolve_keypair()
        if keys is None:
            pytest.skip(
                "langfuse#public_key / langfuse#secret_key not configured — "
                "run `scripts/bootstrap_langfuse.py` then `scripts/seed_vault_dev.py`"
            )
        public_key, secret_key = keys

        tracer = LangfuseTracer(
            public_key=public_key,
            secret_key=secret_key,
            host=LANGFUSE_HOST,
            enabled=True,
        )
        assert tracer.connected, "LangfuseTracer failed to connect under air-gap"

        trace_name = f"airgap-s118-{int(time.time())}"

        async def _drive() -> str:
            tid = await tracer.create_trace(trace_name, {"profile": "A", "source": "s118"})
            sid = await tracer.create_span(tid, "embed", {"dim": 1024})
            await tracer.finish_span(tid, sid, {"ok": True})
            await tracer.finish_trace(tid, {"status": "ok"})
            return tid

        trace_id = asyncio.run(_drive())
        assert trace_id, "trace_id was empty — did LangfuseTracer fail open?"

        assert _poll_trace(public_key, secret_key, trace_name), (
            f"trace {trace_name!r} did not appear in {LANGFUSE_HOST}/api/public/traces — "
            "check Langfuse web container logs"
        )

    def test_bge_m3_encode_under_airgap(self, airgap_guard: None) -> None:
        """Profile A encode works offline once weights are cached locally."""
        if os.getenv("AIFLOW_BGE_M3_WEIGHTS_READY", "0") not in ("1", "true", "yes"):
            pytest.skip(
                "set AIFLOW_BGE_M3_WEIGHTS_READY=1 after running "
                "`scripts/bootstrap_bge_m3.py` to cache the ~2GB model"
            )
        pytest.importorskip("sentence_transformers")

        from aiflow.providers.embedder.bge_m3 import BGEM3Embedder

        embedder = BGEM3Embedder()

        async def _embed() -> list[list[float]]:
            return await embedder.embed(
                ["az AIFlow egy enterprise automatizacios framework", "AIFlow enterprise platform"]
            )

        vectors = asyncio.run(_embed())
        assert len(vectors) == 2
        assert len(vectors[0]) == 1024
        # simple dot-product proxy for cosine (vectors are L2-normalised by BGE-M3)
        dot = sum(a * b for a, b in zip(vectors[0], vectors[1], strict=True))
        assert dot > 0.5, f"unexpectedly low semantic similarity: {dot:.3f}"
