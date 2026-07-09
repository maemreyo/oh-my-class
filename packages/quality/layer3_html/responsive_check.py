"""Responsive check — Playwright-based viewport testing.

Runs viewport tests at 375/768/1280/1920px for staging/prod.
Skipped in development mode.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

VIEWPORT_HEIGHT = 800

_CHECK_VIEWPORT_JS = """() => {
    const body = document.body;
    const html = document.documentElement;
    const scrollWidth = Math.max(body.scrollWidth, html.scrollWidth);
    const clientWidth = html.clientWidth;
    const overflow = scrollWidth > clientWidth;

    const clipping = body.scrollHeight > html.clientHeight
        && getComputedStyle(body).overflow === 'hidden';

    return { overflow, clipping };
}"""


@dataclass
class ResponsiveCheckResult:
    """Result of responsive viewport testing."""

    passed: bool
    viewport_results: dict[int, bool] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


async def check_responsive(
    html: str,
    *,
    viewports: list[int] | None = None,
    environment: str = "development",
) -> ResponsiveCheckResult:
    """Run responsive checks at multiple viewports.

    Args:
        html: HTML content to test.
        viewports: List of viewport widths in px. Default: [375, 768, 1280, 1920]
        environment: Current environment. Skipped in 'development'.

    Returns:
        ResponsiveCheckResult with pass/fail per viewport.
    """
    if viewports is None:
        viewports = [375, 768, 1280, 1920]

    if environment == "development":
        return ResponsiveCheckResult(passed=True)

    try:
        from playwright.async_api import async_playwright  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("playwright not installed — responsive check skipped")
        return ResponsiveCheckResult(
            passed=False,
            issues=["playwright not installed — cannot run responsive viewport checks"],
        )

    viewport_results: dict[int, bool] = {}
    issues: list[str] = []
    all_passed = True

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            for vp in viewports:
                page = await browser.new_page(viewport={"width": vp, "height": VIEWPORT_HEIGHT})
                try:
                    await page.set_content(html, wait_until="networkidle")
                    result = await page.evaluate(_CHECK_VIEWPORT_JS)

                    vp_passed = True
                    if result["overflow"]:
                        vp_passed = False
                        all_passed = False
                        issues.append(f"viewport_{vp}: horizontal overflow (scrollWidth > clientWidth)")

                    if result["clipping"]:
                        vp_passed = False
                        all_passed = False
                        issues.append(f"viewport_{vp}: text clipping (overflow:hidden with content exceeding viewport)")

                    viewport_results[vp] = vp_passed
                finally:
                    await page.close()
        finally:
            await browser.close()

    return ResponsiveCheckResult(
        passed=all_passed,
        viewport_results=viewport_results,
        issues=issues,
    )
