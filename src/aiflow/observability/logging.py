"""Structured JSON logging configuration using structlog.

Usage:
    from aiflow.observability.logging import setup_logging
    setup_logging(log_level="DEBUG", log_format="json")

    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("workflow_started", run_id="abc123", workflow="process-doc")
"""
import logging
import sys
from typing import Literal

import structlog

__all__ = ["setup_logging", "get_logger"]


def setup_logging(
    log_level: str = "INFO",
    log_format: Literal["json", "console"] = "json",
) -> None:
    """Configure structlog for the application.

    Args:
        log_level: Python log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format - 'json' for production, 'console' for dev
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if log_format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Quiet noisy libraries
    for noisy in ("httpx", "httpcore", "asyncio", "urllib3", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger. Convenience wrapper."""
    return structlog.get_logger(name)
