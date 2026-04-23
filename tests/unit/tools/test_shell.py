"""Unit tests for aiflow.tools.shell — coverage uplift (issue #7)."""

from __future__ import annotations

import pytest

from aiflow.tools.shell import (
    ShellCommandDeniedError,
    ShellExecutor,
    ShellResult,
    ShellTimeoutError,
)


def test_shell_result_defaults() -> None:
    res = ShellResult(returncode=0)
    assert res.returncode == 0
    assert res.stdout == ""
    assert res.stderr == ""
    assert res.duration_ms == 0.0
    assert res.command == ""


def test_shell_result_fields() -> None:
    res = ShellResult(
        returncode=1,
        stdout="out",
        stderr="err",
        duration_ms=12.5,
        command="ffprobe x",
    )
    assert res.returncode == 1
    assert res.stdout == "out"
    assert res.duration_ms == 12.5


def test_executor_default_allowed_commands() -> None:
    ex = ShellExecutor()
    assert "ffmpeg" in ex._allowed
    assert "ffprobe" in ex._allowed
    assert "pandoc" in ex._allowed
    assert "kroki" in ex._allowed


def test_executor_custom_allowed_commands() -> None:
    ex = ShellExecutor(allowed_commands={"custom"})
    assert ex._allowed == {"custom"}
    assert "ffmpeg" not in ex._allowed


@pytest.mark.asyncio
async def test_run_empty_command_raises_denied() -> None:
    ex = ShellExecutor()
    with pytest.raises(ShellCommandDeniedError):
        await ex.run([])


@pytest.mark.asyncio
async def test_run_disallowed_command_raises_denied() -> None:
    ex = ShellExecutor()
    with pytest.raises(ShellCommandDeniedError) as exc:
        await ex.run(["rm", "-rf", "/"])
    assert "rm" in str(exc.value)


@pytest.mark.asyncio
async def test_run_path_prefixed_command_checks_basename() -> None:
    """Executable basename is checked, not the full path string."""
    ex = ShellExecutor(allowed_commands={"echo"})
    # /usr/bin/rm has basename 'rm' which is not allowed
    with pytest.raises(ShellCommandDeniedError):
        await ex.run(["/usr/bin/rm", "-rf", "/"])


@pytest.mark.asyncio
async def test_run_allowed_but_missing_binary_raises_denied() -> None:
    """Allowed but not-on-PATH commands raise denied (not-found)."""
    ex = ShellExecutor(allowed_commands={"nonexistent-binary-xyz"})
    with pytest.raises(ShellCommandDeniedError) as exc:
        await ex.run(["nonexistent-binary-xyz"])
    assert "not found on PATH" in str(exc.value)


def test_shell_timeout_error_is_transient() -> None:
    err = ShellTimeoutError("timed out")
    assert err.is_transient is True
    assert err.error_code == "SHELL_TIMEOUT"


def test_shell_command_denied_error_attributes() -> None:
    err = ShellCommandDeniedError("denied")
    assert err.error_code == "SHELL_COMMAND_DENIED"
    assert err.http_status == 403
