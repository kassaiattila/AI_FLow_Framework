"""
@test_registry:
    suite: service-unit
    component: services.document_extractor
    covers: [src/aiflow/services/document_extractor/service.py]
    phase: B2.2
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, document-extractor, extraction, config, sqlalchemy]
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.services.document_extractor.service import (
    DocumentExtractorConfig,
    DocumentExtractorService,
    DocumentTypeConfig,
    FieldDefinition,
)


def _make_config_row():
    """Mock SQLAlchemy result row for document_type_configs."""
    return (
        "cfg-001",  # id
        "invoice-hu",  # name
        "Magyar szamla",  # display_name
        "invoice",  # document_type
        "Hungarian invoice extraction",  # description
        "docling",  # parser
        "openai/gpt-4o",  # extraction_model
        [
            {
                "name": "vendor_name",
                "type": "string",
                "description": "Vendor",
                "required": True,
                "default": None,
            }
        ],
        [],  # validation_rules
        ["json"],  # output_formats
        "default",  # customer
        True,  # enabled
    )


def _make_invoice_row():
    """Mock SQLAlchemy result row for invoices."""
    return (
        "inv-001",  # id
        "test.pdf",  # source_file
        "incoming",  # direction
        "invoice-hu",  # config_name
        "Vendor Kft",  # vendor_name
        "Budapest",  # vendor_address
        "12345678",  # vendor_tax_number
        "Buyer Kft",  # buyer_name
        "Debrecen",  # buyer_address
        "87654321",  # buyer_tax_number
        "INV-2024-001",  # invoice_number
        "2024-01-15",  # invoice_date
        "HUF",  # currency
        100000,  # net_total
        27000,  # vat_total
        127000,  # gross_total
        True,  # is_valid
        [],  # validation_errors
        0.85,  # confidence_score
        "docling",  # parser_used
        False,  # verified
        None,  # verified_by
        None,  # verified_at
        None,  # verified_fields
        "2024-01-15",  # created_at
    )


@pytest.fixture()
def mock_session_factory():
    """Mock SQLAlchemy async session factory."""
    session = AsyncMock()
    factory = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx
    return factory, session


@pytest.fixture()
def svc(mock_session_factory) -> DocumentExtractorService:
    factory, _session = mock_session_factory
    return DocumentExtractorService(session_factory=factory, config=DocumentExtractorConfig())


class TestDocumentExtractorService:
    @pytest.mark.asyncio
    async def test_list_configs(self, svc: DocumentExtractorService, mock_session_factory) -> None:
        """list_configs returns DocumentTypeConfig list."""
        _factory, session = mock_session_factory
        result = MagicMock()
        result.fetchall.return_value = [_make_config_row(), _make_config_row()]
        session.execute = AsyncMock(return_value=result)

        configs = await svc.list_configs()
        assert len(configs) == 2
        assert configs[0].name == "invoice-hu"

    @pytest.mark.asyncio
    async def test_get_config(self, svc: DocumentExtractorService, mock_session_factory) -> None:
        """get_config returns DocumentTypeConfig for existing name."""
        _factory, session = mock_session_factory
        result = MagicMock()
        result.fetchone.return_value = _make_config_row()
        session.execute = AsyncMock(return_value=result)

        config = await svc.get_config("invoice-hu")
        assert config is not None
        assert config.name == "invoice-hu"
        assert config.document_type == "invoice"

    @pytest.mark.asyncio
    async def test_create_config(self, svc: DocumentExtractorService, mock_session_factory) -> None:
        """create_config persists and returns DocumentTypeConfig."""
        _factory, session = mock_session_factory
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        new_config = DocumentTypeConfig(
            name="contract-hu",
            display_name="Magyar szerzodes",
            document_type="contract",
            fields=[FieldDefinition(name="parties", type="string", description="Parties")],
        )
        created = await svc.create_config(new_config)
        assert created.name == "contract-hu"
        assert session.commit.called

    @pytest.mark.asyncio
    async def test_get_invoice(self, svc: DocumentExtractorService, mock_session_factory) -> None:
        """get_invoice returns invoice dict for existing ID."""
        _factory, session = mock_session_factory
        result = MagicMock()
        result.fetchone.return_value = _make_invoice_row()
        session.execute = AsyncMock(return_value=result)

        invoice = await svc.get_invoice("inv-001")
        assert invoice is not None
        assert invoice["id"] == "inv-001"
        assert invoice["vendor_name"] == "Vendor Kft"
        assert invoice["gross_total"] == 127000

    @pytest.mark.asyncio
    async def test_health_check(self, svc: DocumentExtractorService, mock_session_factory) -> None:
        """health_check returns True when DB is accessible."""
        _factory, session = mock_session_factory
        result = MagicMock()
        result.scalar.return_value = 1
        session.execute = AsyncMock(return_value=result)

        assert await svc.health_check() is True
