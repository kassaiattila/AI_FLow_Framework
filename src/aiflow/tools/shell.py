"""Async shell command executor with timeout, logging, and security.

Sandboxed subprocess wrapper for external tools (ffmpeg, ffprobe, pandoc,
kroki).  Commands are validated against an allowed-commands whitelist before
execution to prevent arbitrary shell access.

Note: All I/O is async via ``asyncio.create_subprocess_exec``.

Canonical location: ``aiflow.tools.shell``
Backward-compat re-export: ``aiflow.contrib.shell``
"""
from __future__ import annotations

import asyncio
import json
import shutil
import time
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from aiflow.core.errors import AIFlowError, PermanentError

__all__ = ["ShellExecutor", "ShellResult", "ShellCommandDeniedError", "ShellTimeoutError"]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ShellCommandDeniedError(PermanentError):
    """Raised when a command is not in the allowed whitelist."""

    error_code = "SHELL_COMMAND_DENIED"
    http_status = 403


class ShellTimeoutError(AIFlowError):
    """Raised when a command exceeds its timeout."""

    error_code = "SHELL_TIMEOUT"
    is_transient = True
    http_status = 504


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ShellResult(BaseModel):
    """Result of a shell command execution."""

    returncode: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    command: str = ""


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class ShellExecutor:
    """Async subprocess executor with allowed-commands whitelist.

    Only commands whose executable name appears in ``allowed_commands`` may
    be run.  This prevents accidental or malicious shell access from skills
    and workflows.

    Usage::

        executor = ShellExecutor()
        result = await executor.run(["ffprobe", "-v", "quiet", "video.mp4"])
        print(result.returncode, result.stdout)
    """

    ALLOWED_COMMANDS: set[str] = {"ffmpeg", "ffprobe", "pandoc", "kroki"}

    def __init__(self, allowed_commands: set[str] | None = None) -> None:
        self._allowed = allowed_commands or self.ALLOWED_COMMANDS

    # ------------------------------------------------------------------
    # Core run
    # ------------------------------------------------------------------

    async def run(
        self,
        cmd: list[str],
        timeout: int = 300,
        cwd: Path | None = None,
    ) -> ShellResult:
        """Execute *cmd* asynchronously.

        Parameters
        ----------
        cmd:
            Command as a list of strings.  The first element is validated
            against the allowed whitelist.
        timeout:
            Maximum execution time in seconds (default 300).
        cwd:
            Working directory for the subprocess.

        Returns
        -------
        ShellResult with returncode, stdout, stderr, and timing.

        Raises
        ------
        ShellCommandDeniedError
            If the executable is not in the allowed whitelist.
        ShellTimeoutError
            If the process exceeds *timeout*.
        """
        if not cmd:
            raise ShellCommandDeniedError("Empty command list")

        executable = Path(cmd[0]).name
        if executable not in self._allowed:
            logger.error(
                "shell_command_denied",
                executable=executable,
                allowed=sorted(self._allowed),
            )
            raise ShellCommandDeniedError(
                f"Command '{executable}' is not in allowed list: {sorted(self._allowed)}",
                details={"executable": executable, "allowed": sorted(self._allowed)},
            )

        # Resolve executable path
        resolved = shutil.which(cmd[0])
        if resolved is None:
            raise ShellCommandDeniedError(
                f"Command '{cmd[0]}' not found on PATH",
                details={"executable": cmd[0]},
            )

        command_str = " ".join(cmd)
        logger.info("shell_exec_start", command=command_str, timeout=timeout)
        start = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd) if cwd else None,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            # Try to kill the process on timeout
            try:
                proc.kill()  # type: ignore[union-attr]
                await proc.wait()  # type: ignore[union-attr]
            except ProcessLookupError:
                pass
            duration_ms = (time.monotonic() - start) * 1000
            logger.error(
                "shell_exec_timeout",
                command=command_str,
                timeout=timeout,
                duration_ms=round(duration_ms, 2),
            )
            raise ShellTimeoutError(
                f"Command timed out after {timeout}s: {command_str}",
                details={"command": command_str, "timeout": timeout},
            )

        duration_ms = (time.monotonic() - start) * 1000
        result = ShellResult(
            returncode=proc.returncode or 0,
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
            duration_ms=round(duration_ms, 2),
            command=command_str,
        )

        log_method = logger.info if result.returncode == 0 else logger.warning
        log_method(
            "shell_exec_done",
            command=command_str,
            returncode=result.returncode,
            duration_ms=result.duration_ms,
            stdout_len=len(result.stdout),
            stderr_len=len(result.stderr),
        )
        return result

    # ------------------------------------------------------------------
    # ffprobe convenience
    # ------------------------------------------------------------------

    async def run_ffprobe(self, file_path: str | Path) -> dict[str, Any]:
        """Run ``ffprobe`` on *file_path* and return parsed JSON metadata.

        Returns a dict with ``format`` and ``streams`` keys from ffprobe's
        JSON output.

        Raises
        ------
        FileNotFoundError
            If *file_path* does not exist.
        RuntimeError
            If ffprobe exits with a non-zero returncode.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        result = await self.run(cmd, timeout=60)

        if result.returncode != 0:
            raise RuntimeError(
                f"ffprobe failed (rc={result.returncode}): {result.stderr[:500]}"
            )

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            logger.error(
                "ffprobe_json_parse_error",
                file_path=str(path),
                stdout_preview=result.stdout[:200],
            )
            raise RuntimeError(f"Failed to parse ffprobe JSON output: {exc}") from exc

    # ------------------------------------------------------------------
    # ffmpeg convenience
    # ------------------------------------------------------------------

    async def run_ffmpeg(self, args: list[str], timeout: int = 600) -> ShellResult:
        """Run ``ffmpeg`` with the given *args*.

        Prepends ``ffmpeg`` to *args* automatically.  Uses a longer default
        timeout (600s) since media conversion can be slow.
        """
        cmd = ["ffmpeg"] + args
        return await self.run(cmd, timeout=timeout)
