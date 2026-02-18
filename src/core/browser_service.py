"""
Agent Optimus — Browser Service (FASE 2B).
Playwright headless browser automation for agent web interactions.

Security:
- URL blacklist: no localhost, internal IPs
- Request timeout: 30s max per action
- Context isolation: new browser context per session
- No filesystem access from within browser
"""

import asyncio
import base64
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Security: blocked URL patterns ──────────────────────────────────────────
_BLOCKED_PATTERNS = [
    r"localhost",
    r"127\.0\.0\.",
    r"0\.0\.0\.0",
    r"10\.\d+\.\d+\.\d+",
    r"172\.(1[6-9]|2\d|3[01])\.\d+\.\d+",
    r"192\.168\.\d+\.\d+",
    r"169\.254\.\d+\.\d+",  # link-local
    r"metadata\.google",
    r"169\.254\.169\.254",  # AWS/GCP metadata
]

BROWSER_TIMEOUT_MS = 30_000  # 30s per action
MAX_CONTENT_CHARS = 15_000   # max chars returned from extract


def _check_url_allowed(url: str) -> None:
    """Raise ValueError if URL is on the security blacklist."""
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"URL must start with http:// or https://: {url}")
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            raise ValueError(f"URL blocked for security reasons: {url}")


class BrowserService:
    """
    Manages a single Playwright browser instance for the agent.
    One browser context per request session, auto-cleaned.
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_browser(self):
        """Lazy-initialize the Playwright browser."""
        if self._initialized and self._browser:
            return

        async with self._lock:
            if self._initialized and self._browser:
                return
            try:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-setuid-sandbox",
                    ],
                )
                self._initialized = True
                logger.info("Browser service initialized (Playwright Chromium headless)")
            except Exception as e:
                logger.error(f"Failed to initialize browser: {e}")
                raise RuntimeError(
                    f"Browser unavailable: {e}. "
                    f"Make sure playwright is installed and `playwright install chromium` was run."
                )

    async def _new_context(self):
        """Create a fresh browser context (isolated per request)."""
        await self._ensure_browser()
        return await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            java_script_enabled=True,
            ignore_https_errors=False,
        )

    # ── Public Tools ──────────────────────────────────────────────────────────

    async def navigate(self, url: str) -> dict[str, Any]:
        """
        Navigate to a URL and return page metadata.
        Returns: {url, title, status, content_preview}
        """
        _check_url_allowed(url)
        ctx = await self._new_context()
        try:
            page = await ctx.new_page()
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT_MS)
            title = await page.title()
            status = resp.status if resp else 0

            # Extract readable text preview
            text = await page.evaluate("""() => {
                const els = document.querySelectorAll('p, h1, h2, h3, li');
                return Array.from(els).map(e => e.innerText).join('\\n').slice(0, 2000);
            }""")

            return {
                "url": page.url,
                "title": title,
                "status": status,
                "content_preview": text.strip(),
            }
        finally:
            await ctx.close()

    async def extract(self, url: str, selector: str = "body") -> str:
        """
        Extract text content from a CSS selector on a page.
        Returns the extracted text (max 15k chars).
        """
        _check_url_allowed(url)
        ctx = await self._new_context()
        try:
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT_MS)
            text = await page.evaluate(f"""() => {{
                const els = document.querySelectorAll('{selector}');
                return Array.from(els).map(e => e.innerText).join('\\n---\\n');
            }}""")
            return text.strip()[:MAX_CONTENT_CHARS]
        finally:
            await ctx.close()

    async def search_and_extract(self, url: str, query: str) -> str:
        """
        Navigate to URL, type query in search field, click submit, extract results.
        Useful for search engines and e-commerce sites.
        """
        _check_url_allowed(url)
        ctx = await self._new_context()
        try:
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT_MS)

            # Try common search input selectors
            search_selectors = [
                "input[type='search']",
                "input[name='q']",
                "input[name='query']",
                "input[name='search']",
                "input[placeholder*='busca' i]",
                "input[placeholder*='search' i]",
                "input[placeholder*='pesquis' i]",
            ]
            typed = False
            for sel in search_selectors:
                try:
                    await page.fill(sel, query, timeout=3_000)
                    typed = True
                    break
                except Exception:
                    continue

            if not typed:
                return f"Could not find search input on {url}. Try browser_navigate + browser_extract instead."

            await page.keyboard.press("Enter")
            await page.wait_for_load_state("domcontentloaded", timeout=BROWSER_TIMEOUT_MS)

            # Extract search results
            text = await page.evaluate("""() => {
                const els = document.querySelectorAll('h2, h3, p, [class*="result"], [class*="item"], [class*="product"]');
                return Array.from(els).slice(0, 30).map(e => e.innerText.trim()).filter(t => t.length > 10).join('\\n');
            }""")
            return text.strip()[:MAX_CONTENT_CHARS] or "No results extracted."
        finally:
            await ctx.close()

    async def screenshot(self, url: str) -> str:
        """
        Take a screenshot of a page.
        Returns: base64-encoded PNG string.
        """
        _check_url_allowed(url)
        ctx = await self._new_context()
        try:
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT_MS)
            png_bytes = await page.screenshot(full_page=False, timeout=BROWSER_TIMEOUT_MS)
            return base64.b64encode(png_bytes).decode("utf-8")
        finally:
            await ctx.close()

    async def pdf(self, url: str) -> str:
        """
        Generate a PDF of a page.
        Returns: base64-encoded PDF string.
        """
        _check_url_allowed(url)
        ctx = await self._new_context()
        try:
            page = await ctx.new_page()
            await page.goto(url, wait_until="networkidle", timeout=BROWSER_TIMEOUT_MS)
            pdf_bytes = await page.pdf(format="A4")
            return base64.b64encode(pdf_bytes).decode("utf-8")
        finally:
            await ctx.close()

    async def click_and_extract(self, url: str, click_selector: str, extract_selector: str = "body") -> str:
        """
        Navigate to URL, click an element, extract content after click.
        """
        _check_url_allowed(url)
        ctx = await self._new_context()
        try:
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT_MS)
            await page.click(click_selector, timeout=BROWSER_TIMEOUT_MS)
            await page.wait_for_load_state("domcontentloaded", timeout=10_000)
            text = await page.evaluate(f"""() => {{
                const els = document.querySelectorAll('{extract_selector}');
                return Array.from(els).map(e => e.innerText).join('\\n');
            }}""")
            return text.strip()[:MAX_CONTENT_CHARS]
        finally:
            await ctx.close()

    async def close(self):
        """Shutdown the browser cleanly."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False


# Singleton
browser_service = BrowserService()
