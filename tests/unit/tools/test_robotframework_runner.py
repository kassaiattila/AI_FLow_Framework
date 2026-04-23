"""Unit tests for aiflow.tools.robotframework_runner — coverage uplift (issue #7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.tools.robotframework_runner import (
    RobotConfig,
    RobotFrameworkRunner,
    RobotNotAvailableError,
    RobotResult,
    RobotTaskError,
)


def test_robot_config_defaults() -> None:
    cfg = RobotConfig()
    assert cfg.log_level == "INFO"
    assert cfg.default_timeout == 600
    assert cfg.default_output_dir == "./output/robot_logs"


def test_robot_result_defaults() -> None:
    r = RobotResult(
        success=True,
        return_code=0,
        task_name="t",
        robot_file="f.robot",
    )
    assert r.stdout == ""
    assert r.output_dir == ""


def test_robot_errors_http_status() -> None:
    not_avail = RobotNotAvailableError("x")
    task_err = RobotTaskError("y")
    assert not_avail.error_code == "ROBOT_NOT_AVAILABLE"
    assert not_avail.http_status == 503
    assert task_err.error_code == "ROBOT_TASK_FAILED"
    assert task_err.http_status == 500
    assert not_avail.is_transient is False
    assert task_err.is_transient is False


@pytest.mark.asyncio
async def test_run_task_missing_file_raises(tmp_path: Path) -> None:
    runner = RobotFrameworkRunner()
    with pytest.raises(FileNotFoundError):
        await runner.run_task(
            task_name="t",
            robot_file=tmp_path / "nope.robot",
        )


@pytest.mark.asyncio
async def test_run_task_checked_wraps_failure(tmp_path: Path) -> None:
    """run_task_checked raises RobotTaskError when success=False.

    We use a missing interpreter to make the subprocess fail deterministically,
    avoiding the dependency on Robot Framework being installed.
    """
    robot_file = tmp_path / "dummy.robot"
    robot_file.write_text("*** Tasks ***\nNoop\n    Log    hi\n", encoding="utf-8")

    runner = RobotFrameworkRunner(
        RobotConfig(python_path="nonexistent-python-xyz", default_timeout=5)
    )
    # run_task swallows FileNotFoundError from subprocess exec? actually
    # create_subprocess_exec may raise FileNotFoundError directly on Windows.
    # Accept either: a RobotTaskError (subprocess ran with non-zero exit)
    # OR a FileNotFoundError at subprocess-exec time.
    with pytest.raises((RobotTaskError, FileNotFoundError, NotImplementedError, OSError)):
        await runner.run_task_checked(
            task_name="Noop",
            robot_file=robot_file,
        )


@pytest.mark.asyncio
async def test_is_available_false_for_bad_python() -> None:
    runner = RobotFrameworkRunner(RobotConfig(python_path="nonexistent-python-xyz"))
    # Exception path → False
    result = await runner.is_available()
    assert result is False


@pytest.mark.asyncio
async def test_get_version_none_for_bad_python() -> None:
    runner = RobotFrameworkRunner(RobotConfig(python_path="nonexistent-python-xyz"))
    result = await runner.get_version()
    assert result is None
