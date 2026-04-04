"""Managed async Playwright browser for RPA workflows.

Wraps the Playwright Python async API with session management, cookie
persistence, and common interaction helpers.  Playwright is imported
lazily so the dependency is optional.

Note: Requires ``playwright`` to be installed::

    pip install playwright
    playwright install chromium

Canonical location: ``aiflow.tools.playwright_browser``
Backward-compat re-export: ``aiflow.contrib.playwright``

Usage::

    async with PlaywrightBrowser() as browser:
        await browser.navigate("https://example.com")
        await browser.fill("#search", "hello")
        await browser.click("#submit")
        text = await browser.get_text(".results")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel

__all__ = ["PlaywrightBrowser", "BrowserConfig"]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class BrowserConfig(BaseModel):
    """Configuration for a managed Playwright browser instance."""

    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    timeout_ms: int = 30000
    user_agent: str | None = None
    storage_state_path: str | None = None  # cookie/session persistence
    slow_mo_ms: int = 0  # slow down actions for debugging
    locale: str = "hu-HU"
    timezone_id: str = "Europe/Budapest"


# ---------------------------------------------------------------------------
# Browser wrapper
# ---------------------------------------------------------------------------


class PlaywrightBrowser:
    """Async Playwright browser wrapper with session management.

    Manages the lifecycle of a Chromium browser instance and provides
    simplified methods for common interactions.  Supports async context
    manager protocol for automatic cleanup.
    """

    def __init__(self, config: BrowserConfig | None = None) -> None:
        self.config = config or BrowserConfig()
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def launch(self) -> None:
        """Launch a Chromium browser with the current config.

        Playwright is imported lazily so the dependency stays optional.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            logger.error("playwright_not_installed")
            raise ImportError(
                "playwright is required for PlaywrightBrowser. "
                "Install with: pip install playwright && playwright install chromium"
            ) from exc

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo_ms,
        )

        # Build context options
        context_kwargs: dict[str, Any] = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
            "locale": self.config.locale,
            "timezone_id": self.config.timezone_id,
        }
        if self.config.user_agent:
            context_kwargs["user_agent"] = self.config.user_agent
        if self.config.storage_state_path and Path(self.config.storage_state_path).exists():
            context_kwargs["storage_state"] = self.config.storage_state_path

        self._context = await self._browser.new_context(**context_kwargs)
        self._context.set_default_timeout(self.config.timeout_ms)
        self._page = await self._context.new_page()

        logger.info(
            "playwright_browser_launched",
            headless=self.config.headless,
            viewport=f"{self.config.viewport_width}x{self.config.viewport_height}",
        )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    async def navigate(self, url: str, wait_until: str = "networkidle") -> None:
        """Navigate to *url* and wait for the page to reach *wait_until* state.

        Parameters
        ----------
        url:
            Target URL to navigate to.
        wait_until:
            Playwright wait condition: ``load``, ``domcontentloaded``,
            ``networkidle``, or ``commit``.
        """
        self._ensure_page()
        logger.info("playwright_navigate", url=url, wait_until=wait_until)
        await self._page.goto(url, wait_until=wait_until)

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------

    async def fill(self, selector: str, value: str) -> None:
        """Fill an input field identified by *selector* with *value*."""
        self._ensure_page()
        logger.debug("playwright_fill", selector=selector, value_len=len(value))
        await self._page.fill(selector, value)

    async def click(self, selector: str) -> None:
        """Click the element identified by *selector*."""
        self._ensure_page()
        logger.debug("playwright_click", selector=selector)
        await self._page.click(selector)

    async def check(self, selector: str) -> None:
        """Check a checkbox identified by *selector*."""
        self._ensure_page()
        logger.debug("playwright_check", selector=selector)
        await self._page.check(selector)

    async def wait_for(self, selector: str, timeout: int | None = None) -> None:
        """Wait for an element matching *selector* to appear.

        Parameters
        ----------
        timeout:
            Override timeout in milliseconds.  Uses config default if None.
        """
        self._ensure_page()
        kwargs: dict[str, Any] = {}
        if timeout is not None:
            kwargs["timeout"] = timeout
        logger.debug("playwright_wait_for", selector=selector, timeout=timeout)
        await self._page.wait_for_selector(selector, **kwargs)

    async def get_text(self, selector: str) -> str:
        """Return the inner text of the element matching *selector*."""
        self._ensure_page()
        text = await self._page.inner_text(selector)
        logger.debug("playwright_get_text", selector=selector, text_len=len(text))
        return text

    async def screenshot(self, path: Path) -> bytes:
        """Take a screenshot and save to *path*.

        Returns the screenshot as bytes.
        """
        self._ensure_page()
        path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_bytes: bytes = await self._page.screenshot(path=str(path), full_page=True)
        logger.info("playwright_screenshot", path=str(path), size_bytes=len(screenshot_bytes))
        return screenshot_bytes

    async def evaluate_js(self, script: str) -> Any:
        """Evaluate JavaScript *script* in the page context and return the result."""
        self._ensure_page()
        result = await self._page.evaluate(script)
        logger.debug("playwright_evaluate_js", script_preview=script[:80])
        return result

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    async def save_storage_state(self, path: Path) -> None:
        """Save cookies and local storage to *path* for session reuse."""
        if self._context is None:
            raise RuntimeError("Browser context not initialised. Call launch() first.")
        path.parent.mkdir(parents=True, exist_ok=True)
        await self._context.storage_state(path=str(path))
        logger.info("playwright_storage_state_saved", path=str(path))

    # ------------------------------------------------------------------
    # Cookie / popup handling
    # ------------------------------------------------------------------

    async def dismiss_cookie_popup(
        self,
        selector: str = ".cky-consent-container .cky-btn-accept",
    ) -> None:
        """Attempt to dismiss a cookie consent popup.

        Does nothing if the popup element is not found within 3 seconds.
        """
        self._ensure_page()
        try:
            await self._page.wait_for_selector(selector, timeout=3000)
            await self._page.click(selector)
            logger.info("playwright_cookie_dismissed", selector=selector)
        except Exception:
            logger.debug("playwright_cookie_not_found", selector=selector)

    # ------------------------------------------------------------------
    # Page property
    # ------------------------------------------------------------------

    @property
    def page(self) -> Any:
        """Direct access to the underlying Playwright Page for advanced usage."""
        return self._page

    @property
    def context(self) -> Any:
        """Direct access to the underlying Playwright BrowserContext."""
        return self._context

    @property
    def is_launched(self) -> bool:
        """Return True if the browser has been launched."""
        return self._browser is not None

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close browser, context, and Playwright process."""
        if self._context is not None:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
            self._page = None

        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

        logger.info("playwright_browser_closed")

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> PlaywrightBrowser:
        await self.launch()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_page(self) -> None:
        """Raise if the browser page is not initialised."""
        if self._page is None:
            raise RuntimeError("Browser page not initialised. Call launch() or use 'async with'.")
