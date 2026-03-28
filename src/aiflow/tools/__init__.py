"""AIFlow tools - unified external tool runners.

All contrib modules are re-exported here as the canonical location.
Backward-compat imports from ``aiflow.contrib.*`` still work via re-exports.
"""
from aiflow.tools.robotframework_runner import RobotFrameworkRunner, RobotResult, RobotConfig
from aiflow.tools.shell import ShellExecutor, ShellResult, ShellCommandDeniedError, ShellTimeoutError
from aiflow.tools.playwright_browser import PlaywrightBrowser, BrowserConfig
from aiflow.tools.human_loop import HumanLoopManager, HumanLoopResponse, ApprovalRequest
from aiflow.tools.kafka import KafkaConfig, KafkaProducer, KafkaConsumer

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
]
