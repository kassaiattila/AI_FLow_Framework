"""Robot Framework task runner for AIFlow RPA skills.

Executes .robot task files via subprocess, passing variables from config.
Used by skills that need browser automation with Robot Framework's
Browser library (Playwright wrapper with RF keywords).

Usage:
    runner = RobotFrameworkRunner()
    result = await runner.run_task(
        task_name="Login_If_Needed",
        robot_file=Path("skills/cubix_course_capture/robot/login.robot"),
        variables={"CUBIX_EMAIL": "user@example.com", "CUBIX_PASSWORD": "pass"},
        output_dir=Path("output/robot_logs"),
    )
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import structlog
from pydantic import BaseModel

from aiflow.core.errors import AIFlowError

__all__ = [
    "RobotFrameworkRunner",
    "RobotResult",
    "RobotConfig",
    "RobotNotAvailableError",
    "RobotTaskError",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class RobotNotAvailableError(AIFlowError):
    """Raised when Robot Framework is not installed or not reachable."""

    error_code = "ROBOT_NOT_AVAILABLE"
    is_transient = False
    http_status = 503


class RobotTaskError(AIFlowError):
    """Raised when a Robot Framework task fails."""

    error_code = "ROBOT_TASK_FAILED"
    is_transient = False
    http_status = 500


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RobotConfig(BaseModel):
    """Configuration for Robot Framework execution."""

    python_path: str = sys.executable
    log_level: str = "INFO"
    default_timeout: int = 600  # seconds
    default_output_dir: str = "./output/robot_logs"


class RobotResult(BaseModel):
    """Result of a Robot Framework task execution."""

    success: bool
    return_code: int
    task_name: str
    robot_file: str
    output_dir: str = ""
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    # Paths to RF output files
    log_html: str = ""
    report_html: str = ""
    output_xml: str = ""


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class RobotFrameworkRunner:
    """Execute Robot Framework .robot tasks as async subprocess calls.

    Wraps the ``python -m robot`` invocation in an async subprocess, passing
    variables as ``--variable KEY:VALUE`` pairs. Output files (log.html,
    report.html, output.xml) are written to the configured output directory.

    This runner is modelled after the pilot project's ``run_robot.py`` but
    designed as a reusable async service for AIFlow's DI container.
    """

    def __init__(self, config: RobotConfig | None = None) -> None:
        self.config = config or RobotConfig()

    async def run_task(
        self,
        task_name: str,
        robot_file: Path | str,
        variables: dict[str, str] | None = None,
        output_dir: Path | str | None = None,
        timeout: int | None = None,
    ) -> RobotResult:
        """Execute a single Robot Framework task.

        Args:
            task_name: The task name defined in the .robot file
                       (e.g., ``"Login_If_Needed"``).
            robot_file: Path to the .robot file.
            variables: Robot Framework variables passed as
                       ``--variable KEY:VALUE`` pairs.
            output_dir: Where to write RF log/report/output files.
            timeout: Max execution time in seconds.

        Returns:
            RobotResult with success status, stdout/stderr, and output paths.

        Raises:
            FileNotFoundError: If *robot_file* does not exist.
        """
        robot_file = Path(robot_file)
        if not robot_file.exists():
            raise FileNotFoundError(f"Robot file not found: {robot_file}")

        out_dir = Path(output_dir or self.config.default_output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Build command
        cmd = [
            self.config.python_path,
            "-m",
            "robot",
            "--task",
            task_name,
            "--outputdir",
            str(out_dir),
            "--loglevel",
            self.config.log_level,
        ]

        # Add variables
        if variables:
            for key, value in variables.items():
                cmd.extend(["--variable", f"{key}:{value}"])

        # Add robot file
        cmd.append(str(robot_file))

        logger.info(
            "robot_task_start",
            task=task_name,
            robot_file=str(robot_file),
            variables_count=len(variables or {}),
        )

        start = time.monotonic()
        effective_timeout = timeout or self.config.default_timeout

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(robot_file.parent.parent),  # skill root directory
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=effective_timeout,
            )

            duration = (time.monotonic() - start) * 1000
            success = proc.returncode == 0

            result = RobotResult(
                success=success,
                return_code=proc.returncode or 0,
                task_name=task_name,
                robot_file=str(robot_file),
                output_dir=str(out_dir),
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                duration_ms=round(duration, 2),
                log_html=(str(out_dir / "log.html") if (out_dir / "log.html").exists() else ""),
                report_html=(
                    str(out_dir / "report.html") if (out_dir / "report.html").exists() else ""
                ),
                output_xml=(
                    str(out_dir / "output.xml") if (out_dir / "output.xml").exists() else ""
                ),
            )

            logger.info(
                "robot_task_done",
                task=task_name,
                success=success,
                return_code=proc.returncode,
                duration_ms=round(duration),
            )

            return result

        except TimeoutError:
            duration = (time.monotonic() - start) * 1000
            logger.error("robot_task_timeout", task=task_name, timeout=effective_timeout)
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass
            return RobotResult(
                success=False,
                return_code=-1,
                task_name=task_name,
                robot_file=str(robot_file),
                stderr=f"Timeout after {effective_timeout}s",
                duration_ms=round(duration, 2),
            )

    async def run_task_checked(
        self,
        task_name: str,
        robot_file: Path | str,
        variables: dict[str, str] | None = None,
        output_dir: Path | str | None = None,
        timeout: int | None = None,
    ) -> RobotResult:
        """Like :meth:`run_task` but raises :class:`RobotTaskError` on failure.

        Convenience wrapper for callers that want exception-based error
        handling instead of checking ``result.success``.
        """
        result = await self.run_task(
            task_name=task_name,
            robot_file=robot_file,
            variables=variables,
            output_dir=output_dir,
            timeout=timeout,
        )
        if not result.success:
            raise RobotTaskError(
                f"Robot task '{task_name}' failed (rc={result.return_code})",
                details={
                    "task": task_name,
                    "robot_file": str(robot_file),
                    "return_code": result.return_code,
                    "stderr": result.stderr[:1000],
                },
            )
        return result

    async def is_available(self) -> bool:
        """Check if Robot Framework is installed and reachable."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.config.python_path,
                "-m",
                "robot",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            # RF --version returns 251, not 0 (known RF behavior)
            output = (stdout or stderr or b"").decode("utf-8", errors="replace")
            return "Robot Framework" in output
        except Exception:
            return False

    async def get_version(self) -> str | None:
        """Return the Robot Framework version string, or None if unavailable."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.config.python_path,
                "-m",
                "robot",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = (stdout or stderr or b"").decode("utf-8", errors="replace").strip()
            if "Robot Framework" in output:
                return output
            return None
        except Exception:
            return None
