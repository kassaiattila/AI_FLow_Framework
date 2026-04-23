"""Unit tests for aiflow.tools.playwright_browser — coverage uplift (issue #7).

Playwright itself is an optional dep; these tests only exercise the bits that
don't need a live browser (config, lifecycle guards, uninitialised-state
errors).
"""

from __future__ import annotations

import pytest

from aiflow.tools.playwright_browser import BrowserConfig, PlaywrightBrowser


def test_browser_config_defaults() -> None:
    cfg = BrowserConfig()
    assert cfg.headless is True
    assert cfg.viewport_width == 1920
    assert cfg.viewport_height == 1080
    assert cfg.timeout_ms == 30000
    assert cfg.locale == "hu-HU"
    assert cfg.timezone_id == "Europe/Budapest"
    assert cfg.user_agent is None
    assert cfg.slow_mo_ms == 0


def test_browser_config_custom() -> None:
    cfg = BrowserConfig(headless=False, viewport_width=800, user_agent="UA")
    assert cfg.headless is False
    assert cfg.viewport_width == 800
    assert cfg.user_agent == "UA"


def test_not_launched_by_default() -> None:
    b = PlaywrightBrowser()
    assert b.is_launched is False
    assert b.page is None
    assert b.context is None


def test_ensure_page_raises_before_launch() -> None:
    b = PlaywrightBrowser()
    with pytest.raises(RuntimeError, match="page not initialised"):
        b._ensure_page()


@pytest.mark.asyncio
async def test_navigate_without_launch_raises() -> None:
    b = PlaywrightBrowser()
    with pytest.raises(RuntimeError):
        await b.navigate("https://example.com")


@pytest.mark.asyncio
async def test_fill_without_launch_raises() -> None:
    b = PlaywrightBrowser()
    with pytest.raises(RuntimeError):
        await b.fill("#x", "v")


@pytest.mark.asyncio
async def test_click_without_launch_raises() -> None:
    b = PlaywrightBrowser()
    with pytest.raises(RuntimeError):
        await b.click("#x")


@pytest.mark.asyncio
async def test_get_text_without_launch_raises() -> None:
    b = PlaywrightBrowser()
    with pytest.raises(RuntimeError):
        await b.get_text("#x")


@pytest.mark.asyncio
async def test_save_storage_state_without_launch_raises(tmp_path) -> None:
    b = PlaywrightBrowser()
    with pytest.raises(RuntimeError, match="Browser context not initialised"):
        await b.save_storage_state(tmp_path / "state.json")


@pytest.mark.asyncio
async def test_close_is_idempotent_when_never_launched() -> None:
    b = PlaywrightBrowser()
    await b.close()  # no raise
    assert b.is_launched is False
