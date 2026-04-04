"""Shell command execution for AIFlow (ffmpeg, ffprobe, etc.).

Backward-compat re-export. Canonical location: ``aiflow.tools.shell``
"""

from aiflow.tools.shell import (
    ShellCommandDeniedError,
    ShellExecutor,
    ShellResult,
    ShellTimeoutError,
)

__all__ = ["ShellExecutor", "ShellResult", "ShellCommandDeniedError", "ShellTimeoutError"]
