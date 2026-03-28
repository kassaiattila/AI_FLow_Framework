"""
@test_registry:
    suite: core-unit
    component: observability.logging
    covers: [src/aiflow/observability/logging.py]
    phase: 1
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [observability, logging, structlog]
"""
import logging

import structlog

from aiflow.observability.logging import setup_logging, get_logger


class TestSetupLogging:
    def test_setup_json_format(self):
        setup_logging(log_level="DEBUG", log_format="json")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1

    def test_setup_console_format(self):
        setup_logging(log_level="INFO", log_format="console")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_noisy_loggers_silenced(self):
        setup_logging()
        assert logging.getLogger("httpx").level >= logging.WARNING
        assert logging.getLogger("sqlalchemy.engine").level >= logging.WARNING

    def test_structlog_produces_output(self, capsys):
        setup_logging(log_level="INFO", log_format="console")
        logger = structlog.get_logger("test")
        logger.info("test_event", key="value")
        captured = capsys.readouterr()
        assert "test_event" in captured.out


class TestGetLogger:
    def test_returns_bound_logger(self):
        logger = get_logger("test.module")
        assert logger is not None

    def test_logger_has_methods(self):
        logger = get_logger("test")
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
