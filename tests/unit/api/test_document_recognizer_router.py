"""
@test_registry:
    suite: api-unit
    component: api.v1.document_recognizer
    covers:
        - src/aiflow/api/v1/document_recognizer.py
    phase: v1.6.0
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [unit, api, doc_recognizer, sprint_v, sv_3]
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import yaml
from fastapi.testclient import TestClient

from aiflow.contracts.doc_recognition import (
    DocTypeDescriptor,
    ExtractionConfig,
    FieldSpec,
    IntentRoutingConfig,
    RuleSpec,
    TypeClassifierConfig,
)
from aiflow.security.auth import AuthProvider


def _invoice_descriptor() -> DocTypeDescriptor:
    return DocTypeDescriptor(
        name="hu_invoice",
        display_name="HU Invoice",
        type_classifier=TypeClassifierConfig(
            rules=[RuleSpec(kind="regex", weight=1.0, pattern=r"\bSzámla\b")]
        ),
        extraction=ExtractionConfig(
            workflow="invoice_extraction_chain",
            fields=[FieldSpec(name="invoice_number", type="string", required=True)],
        ),
        intent_routing=IntentRoutingConfig(default="process"),
    )


def _id_card_descriptor() -> DocTypeDescriptor:
    return DocTypeDescriptor(
        name="hu_id_card",
        display_name="HU ID card",
        pii_level="high",
        type_classifier=TypeClassifierConfig(
            rules=[RuleSpec(kind="regex", weight=1.0, pattern=r"MAGYARORSZÁG")]
        ),
        extraction=ExtractionConfig(
            workflow="id_card_extraction_chain",
            fields=[FieldSpec(name="id_number", type="string", required=True)],
        ),
        intent_routing=IntentRoutingConfig(default="route_to_human", pii_redaction=True),
    )


@contextmanager
def _client_and_headers(tenant_id: str = "t1"):
    """Build TestClient + auth header in one shot. Mirrors S144 / S151 pattern.

    Auth is provider-instance bound: tokens only verify on the same
    AuthProvider that signed them. AuthMiddleware.__init__ runs lazily on
    first request, so the patch must cover create_app + warmup + request.
    """
    auth = AuthProvider.from_env()
    with patch.object(AuthProvider, "from_env", return_value=auth):
        from aiflow.api.app import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        client.get("/health/live")  # warmup the middleware inside the patch
        token = auth.create_token(user_id=tenant_id, role="admin")
        yield client, {"Authorization": f"Bearer {token}"}


def _patch_orchestrator(*, descriptors: list[DocTypeDescriptor], result):
    """Patch the module-level orchestrator singleton + its repository writer."""
    fake_orchestrator = MagicMock()
    fake_registry = MagicMock()

    def list_doctypes(tenant_id=None):
        return descriptors

    def get_doctype(name, tenant_id=None):
        for d in descriptors:
            if d.name == name:
                return d
        return None

    fake_registry.list_doctypes = list_doctypes
    fake_registry.get_doctype = get_doctype
    fake_registry.invalidate_cache = MagicMock()

    fake_orchestrator._registry = fake_registry
    fake_orchestrator.run = AsyncMock(return_value=result)
    return fake_orchestrator


# ---------------------------------------------------------------------------
# GET /api/v1/document-recognizer/doctypes
# ---------------------------------------------------------------------------


class TestListDoctypes:
    def test_lists_two_doctypes(self):
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.document_recognizer.get_orchestrator",
                return_value=_patch_orchestrator(
                    descriptors=[_invoice_descriptor(), _id_card_descriptor()],
                    result=None,
                ),
            ),
        ):
            resp = client.get("/api/v1/document-recognizer/doctypes", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        names = sorted(item["name"] for item in body["items"])
        assert names == ["hu_id_card", "hu_invoice"]

    def test_requires_auth(self):
        with _client_and_headers() as (client, _headers):
            resp = client.get("/api/v1/document-recognizer/doctypes")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/document-recognizer/doctypes/{name}
# ---------------------------------------------------------------------------


class TestGetDoctype:
    def test_known_doctype(self):
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.document_recognizer.get_orchestrator",
                return_value=_patch_orchestrator(
                    descriptors=[_invoice_descriptor()],
                    result=None,
                ),
            ),
        ):
            resp = client.get(
                "/api/v1/document-recognizer/doctypes/hu_invoice",
                headers=headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["descriptor"]["name"] == "hu_invoice"
        assert body["source"] in ("bootstrap", "tenant_override")

    def test_unknown_doctype_returns_404(self):
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.document_recognizer.get_orchestrator",
                return_value=_patch_orchestrator(
                    descriptors=[_invoice_descriptor()],
                    result=None,
                ),
            ),
        ):
            resp = client.get(
                "/api/v1/document-recognizer/doctypes/nonexistent",
                headers=headers,
            )
        assert resp.status_code == 404

    def test_invalid_name_returns_400(self):
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.document_recognizer.get_orchestrator",
                return_value=_patch_orchestrator(descriptors=[], result=None),
            ),
        ):
            resp = client.get(
                "/api/v1/document-recognizer/doctypes/HU-Invoice",  # uppercase + hyphen disallowed
                headers=headers,
            )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# PUT /api/v1/document-recognizer/doctypes/{name}
# ---------------------------------------------------------------------------


class TestUpsertTenantOverride:
    def test_invalid_yaml_returns_400(self):
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.document_recognizer.get_orchestrator",
                return_value=_patch_orchestrator(descriptors=[], result=None),
            ),
        ):
            resp = client.put(
                "/api/v1/document-recognizer/doctypes/hu_invoice",
                json={"yaml_text": "name: hu_invoice\nlevel: [unclosed"},
                headers=headers,
            )
        assert resp.status_code == 400

    def test_descriptor_name_mismatch_returns_400(self, tmp_path):
        descriptor = _invoice_descriptor()
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.document_recognizer.get_orchestrator",
                return_value=_patch_orchestrator(
                    descriptors=[descriptor],
                    result=None,
                ),
            ),
            patch(
                "aiflow.api.v1.document_recognizer._tenant_overrides_dir",
                return_value=tmp_path / "overrides",
            ),
        ):
            resp = client.put(
                "/api/v1/document-recognizer/doctypes/hu_id_card",  # mismatched path
                json={"descriptor": descriptor.model_dump(mode="json", by_alias=True)},
                headers=headers,
            )
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"]

    def test_writes_override_file(self, tmp_path):
        descriptor = _invoice_descriptor()
        # The orchestrator's invalidate_cache is just a MagicMock — fine.
        with (
            _client_and_headers(tenant_id="acme") as (client, headers),
            patch(
                "aiflow.api.v1.document_recognizer.get_orchestrator",
                return_value=_patch_orchestrator(descriptors=[descriptor], result=None),
            ),
            patch(
                "aiflow.api.v1.document_recognizer._tenant_overrides_dir",
                return_value=tmp_path / "overrides",
            ),
        ):
            resp = client.put(
                "/api/v1/document-recognizer/doctypes/hu_invoice",
                json={"descriptor": descriptor.model_dump(mode="json", by_alias=True)},
                headers=headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "hu_invoice"
        assert body["tenant_id"] == "acme"
        target = tmp_path / "overrides" / "acme" / "hu_invoice.yaml"
        assert target.exists()
        # Verify it Pydantic-validates round-trip
        payload = yaml.safe_load(target.read_text(encoding="utf-8"))
        round_trip = DocTypeDescriptor.model_validate(payload)
        assert round_trip.name == "hu_invoice"


# ---------------------------------------------------------------------------
# DELETE /api/v1/document-recognizer/doctypes/{name}
# ---------------------------------------------------------------------------


class TestDeleteTenantOverride:
    def test_missing_override_returns_404(self, tmp_path):
        with (
            _client_and_headers(tenant_id="acme") as (client, headers),
            patch(
                "aiflow.api.v1.document_recognizer.get_orchestrator",
                return_value=_patch_orchestrator(descriptors=[], result=None),
            ),
            patch(
                "aiflow.api.v1.document_recognizer._tenant_overrides_dir",
                return_value=tmp_path / "overrides",
            ),
        ):
            resp = client.delete(
                "/api/v1/document-recognizer/doctypes/hu_invoice",
                headers=headers,
            )
        assert resp.status_code == 404

    def test_deletes_existing_override(self, tmp_path):
        # Pre-create the override file
        target_dir = tmp_path / "overrides" / "acme"
        target_dir.mkdir(parents=True)
        target = target_dir / "hu_invoice.yaml"
        target.write_text("name: hu_invoice", encoding="utf-8")

        with (
            _client_and_headers(tenant_id="acme") as (client, headers),
            patch(
                "aiflow.api.v1.document_recognizer.get_orchestrator",
                return_value=_patch_orchestrator(descriptors=[], result=None),
            ),
            patch(
                "aiflow.api.v1.document_recognizer._tenant_overrides_dir",
                return_value=tmp_path / "overrides",
            ),
        ):
            resp = client.delete(
                "/api/v1/document-recognizer/doctypes/hu_invoice",
                headers=headers,
            )
        assert resp.status_code == 204
        assert not target.exists()


# ---------------------------------------------------------------------------
# POST /api/v1/document-recognizer/recognize
# ---------------------------------------------------------------------------


class TestRecognizeEndpoint:
    def test_no_file_returns_400(self):
        with _client_and_headers() as (client, headers):
            resp = client.post(
                "/api/v1/document-recognizer/recognize",
                files={},
                headers=headers,
            )
        # FastAPI 422 for missing required form field
        assert resp.status_code in (400, 422)

    def test_empty_upload_returns_400(self):
        with _client_and_headers() as (client, headers):
            resp = client.post(
                "/api/v1/document-recognizer/recognize",
                files={"file": ("empty.txt", b"", "text/plain")},
                headers=headers,
            )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Path traversal guards
# ---------------------------------------------------------------------------


class TestPathTraversalGuard:
    def test_put_rejects_invalid_doctype_name(self, tmp_path):
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.document_recognizer.get_orchestrator",
                return_value=_patch_orchestrator(descriptors=[], result=None),
            ),
            patch(
                "aiflow.api.v1.document_recognizer._tenant_overrides_dir",
                return_value=tmp_path / "overrides",
            ),
        ):
            resp = client.put(
                "/api/v1/document-recognizer/doctypes/..%2Fmalicious",
                json={"yaml_text": "name: x"},
                headers=headers,
            )
        # Either FastAPI 404 (path didn't match route) or 400 (validation fired)
        assert resp.status_code in (400, 404)

    def test_delete_rejects_invalid_doctype_name(self, tmp_path):
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.document_recognizer.get_orchestrator",
                return_value=_patch_orchestrator(descriptors=[], result=None),
            ),
            patch(
                "aiflow.api.v1.document_recognizer._tenant_overrides_dir",
                return_value=tmp_path / "overrides",
            ),
        ):
            resp = client.delete(
                "/api/v1/document-recognizer/doctypes/HU-Bad-Name",
                headers=headers,
            )
        assert resp.status_code in (400, 404)
