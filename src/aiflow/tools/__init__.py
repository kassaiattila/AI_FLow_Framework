"""AIFlow tools - unified external tool runners.

All contrib modules are re-exported here as the canonical location.
Backward-compat imports from ``aiflow.contrib.*`` still work via re-exports.
"""
from aiflow.tools.attachment_processor import (
    AttachmentConfig,
    AttachmentProcessor,
    ProcessedAttachment,
)
from aiflow.tools.azure_doc_intelligence import AzureDocIntelligence
from aiflow.tools.email_parser import EmailAttachment, EmailParser, ParsedEmail
from aiflow.tools.human_loop import ApprovalRequest, HumanLoopManager, HumanLoopResponse
from aiflow.tools.kafka import KafkaConfig, KafkaConsumer, KafkaProducer
from aiflow.tools.playwright_browser import BrowserConfig, PlaywrightBrowser
from aiflow.tools.robotframework_runner import RobotConfig, RobotFrameworkRunner, RobotResult
from aiflow.tools.schema_registry import SchemaRegistry
from aiflow.tools.shell import (
    ShellCommandDeniedError,
    ShellExecutor,
    ShellResult,
    ShellTimeoutError,
)

__all__ = [
    # Robot Framework
    "RobotFrameworkRunner",
    "RobotResult",
    "RobotConfig",
    # Shell executor
    "ShellExecutor",
    "ShellResult",
    "ShellCommandDeniedError",
    "ShellTimeoutError",
    # Playwright browser
    "PlaywrightBrowser",
    "BrowserConfig",
    # Human loop
    "HumanLoopManager",
    "HumanLoopResponse",
    "ApprovalRequest",
    # Kafka
    "KafkaConfig",
    "KafkaProducer",
    "KafkaConsumer",
    # Email processing
    "EmailParser",
    "ParsedEmail",
    "EmailAttachment",
    # Attachment processing
    "AttachmentProcessor",
    "ProcessedAttachment",
    "AttachmentConfig",
    # Azure Document Intelligence
    "AzureDocIntelligence",
    # Schema registry
    "SchemaRegistry",
]
