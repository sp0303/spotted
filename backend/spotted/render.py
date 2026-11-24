"""Render a page in headless Chromium (Playwright) for the raw-vs-rendered comparison.

Optional: if Playwright or a browser isn't available, the JavaScript check falls back to the raw
HTML alone and says so. Every request the page makes is checked against private addresses.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

from .config import settings
from .crawl import FetchError, assert_public_host

log = logging.getLogger(__name__)


@dataclass
class RenderResult:
    url: str
    text: str
    words: int
    links: int


class Renderer(Protocol):
    async def render(self, url: str) -> RenderResult | None: ...


class PlaywrightRenderer:
    async def render(self, url: str) -> RenderResult | None:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None
        try:
            return await asyncio.wait_for(self._render(async_playwright, url), timeout=settings.render_timeout_s)
        except Exception as exc:  # rendering is best-effort; the check reports when it didn't run
            log.warning("render failed for %s: %s", url, exc)
            return None

    async def _render(self, async_playwright, url: str) -> RenderResult:
        async with async_playwright() as p:
            kwargs = {"executable_path": settings.chromium_path} if settings.chromium_path else {}
            browser = await p.chromium.launch(**kwargs)
            try:
                page = await browser.new_page()

                async def guard(route):
                    host = urlsplit(route.request.url).hostname
                    if route.request.resource_type in ("image", "media", "font"):
                        return await route.abort()
                    try:
                        if host:
                            await assert_public_host(host)
                    except FetchError:
                        return await route.abort()
                    await route.continue_()

                await page.route("**/*", guard)
                await page.goto(url, wait_until="networkidle", timeout=settings.render_timeout_s * 1000)
                text = await page.evaluate("document.body ? document.body.innerText : ''")
                links = await page.evaluate("document.querySelectorAll('a[href]').length")
                return RenderResult(url=page.url, text=text, words=len(re.findall(r"\w+", text)), links=links)
            finally:
                await browser.close()


def default_renderer() -> Renderer | None:
    if settings.chromium_path == "off":
        return None
    return PlaywrightRenderer()
