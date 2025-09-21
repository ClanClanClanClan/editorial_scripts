"""Unified browser facade to abstract Playwright/Selenium differences.

Provides a minimal async interface used by adapters and auth flows, with two
implementations:
- PlaywrightFacade: wraps PlaywrightManager (native async)
- SeleniumFacade: wraps Selenium BrowserManager via threads (best‑effort)
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.ecc.adapters.browser.playwright_manager import (
    PlaywrightConfig,
    PlaywrightManager,
)
from src.ecc.core.browser_manager import BrowserManager as SeleniumBrowserManager
from src.ecc.core.logging_system import ExtractorLogger


class BrowserFacade(ABC):
    @abstractmethod
    async def __aenter__(self) -> BrowserFacade: ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    @abstractmethod
    async def navigate_to(
        self, url: str, wait_until: str = "networkidle", wait_for_selector: str | None = None
    ) -> None: ...

    @abstractmethod
    async def fill_input(self, selector: str, value: str) -> bool: ...

    @abstractmethod
    async def click_element(self, selector: str) -> bool: ...

    @abstractmethod
    async def wait_for_selector(self, selector: str) -> Any: ...

    @abstractmethod
    async def get_text(self, selector: str) -> str | None: ...

    @abstractmethod
    async def get_cookies(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def take_screenshot(self, path: Path | None = None, full_page: bool = False) -> Path: ...


class PlaywrightFacade(BrowserFacade):
    def __init__(
        self, config: PlaywrightConfig | None = None, logger: ExtractorLogger | None = None
    ):
        self.config = config or PlaywrightConfig(headless=True)
        self.logger = logger or ExtractorLogger("browser_facade")
        self._mgr: PlaywrightManager | None = None

    async def __aenter__(self) -> BrowserFacade:
        self._mgr = PlaywrightManager(self.config, self.logger)
        await self._mgr.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._mgr:
            await self._mgr.__aexit__(exc_type, exc, tb)
            self._mgr = None

    async def navigate_to(
        self, url: str, wait_until: str = "networkidle", wait_for_selector: str | None = None
    ) -> None:
        assert self._mgr
        await self._mgr.navigate_to(url, wait_until=wait_until, wait_for_selector=wait_for_selector)

    async def fill_input(self, selector: str, value: str) -> bool:
        assert self._mgr
        return await self._mgr.fill_input(selector, value)

    async def click_element(self, selector: str) -> bool:
        assert self._mgr
        return await self._mgr.click_element(selector)

    async def wait_for_selector(self, selector: str) -> Any:
        assert self._mgr
        return await self._mgr.wait_for_selector(selector)

    async def get_text(self, selector: str) -> str | None:
        assert self._mgr
        return await self._mgr.get_text(selector)

    async def get_cookies(self) -> list[dict[str, Any]]:
        assert self._mgr and self._mgr.context
        return await self._mgr.get_cookies()

    async def take_screenshot(self, path: Path | None = None, full_page: bool = False) -> Path:
        assert self._mgr
        return await self._mgr.take_screenshot(path, full_page)


class SeleniumFacade(BrowserFacade):
    """Async wrapper around the synchronous Selenium BrowserManager.

    This is best‑effort and uses threads to avoid blocking the event loop.
    """

    def __init__(self, logger: ExtractorLogger | None = None):
        self.logger = logger or ExtractorLogger("browser_facade")
        self._mgr: SeleniumBrowserManager | None = None

    async def __aenter__(self) -> BrowserFacade:
        def _setup():
            self._mgr = SeleniumBrowserManager(logger=self.logger)
            self._mgr.setup_driver()

        await asyncio.to_thread(_setup)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._mgr:
            await asyncio.to_thread(self._mgr.cleanup)
            self._mgr = None

    async def navigate_to(
        self, url: str, wait_until: str = "networkidle", wait_for_selector: str | None = None
    ) -> None:
        assert self._mgr
        await asyncio.to_thread(self._mgr.navigate_to, url, None)
        if wait_for_selector:
            from selenium.webdriver.common.by import By

            await asyncio.to_thread(self._mgr.wait_for_element, By.CSS_SELECTOR, wait_for_selector)

    async def fill_input(self, selector: str, value: str) -> bool:
        assert self._mgr and self._mgr.driver
        from selenium.webdriver.common.by import By

        def _do():
            el = self._mgr.driver.find_element(By.CSS_SELECTOR, selector)
            el.clear()
            el.send_keys(value)
            return True

        return await asyncio.to_thread(_do)

    async def click_element(self, selector: str) -> bool:
        assert self._mgr and self._mgr.driver
        from selenium.webdriver.common.by import By

        def _do():
            el = self._mgr.driver.find_element(By.CSS_SELECTOR, selector)
            return self._mgr.safe_click(el)

        return await asyncio.to_thread(_do)

    async def wait_for_selector(self, selector: str) -> Any:
        assert self._mgr
        from selenium.webdriver.common.by import By

        return await asyncio.to_thread(self._mgr.wait_for_element, By.CSS_SELECTOR, selector)

    async def get_text(self, selector: str) -> str | None:
        assert self._mgr and self._mgr.driver
        from selenium.webdriver.common.by import By

        def _do():
            el = self._mgr.driver.find_element(By.CSS_SELECTOR, selector)
            return el.text

        return await asyncio.to_thread(_do)

    async def get_cookies(self) -> list[dict[str, Any]]:
        assert self._mgr and self._mgr.driver

        def _do():
            return self._mgr.driver.get_cookies() or []

        return await asyncio.to_thread(_do)

    async def take_screenshot(self, path: Path | None = None, full_page: bool = False) -> Path:
        assert self._mgr

        def _do() -> Path:
            from datetime import UTC, datetime

            p = path or (
                self._mgr.config.download_dir
                / "screenshots"
                / f"screenshot_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.png"
            )
            p.parent.mkdir(exist_ok=True)
            self._mgr.driver.save_screenshot(str(p))
            return p

        return await asyncio.to_thread(_do)
