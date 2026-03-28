"""
@test_registry:
    suite: api-unit
    component: api.app
    covers: [src/aiflow/api/app.py]
    phase: 5
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [api, fastapi, app-factory]
"""
import pytest
from fastapi import FastAPI
from aiflow.api.app import create_app
from aiflow._version import __version__


class TestCreateApp:
    def test_returns_fastapi_instance(self):
        app = create_app()
        assert isinstance(app, FastAPI)

    def test_has_correct_version(self):
        app = create_app()
        assert app.version == __version__

    def test_has_docs_url(self):
        app = create_app()
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
