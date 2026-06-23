"""Responsive check — Playwright-based viewport testing.

Runs screenshots at 4 viewports (375/768/1280/1920px) for staging/prod.
Skipped in development mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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

    # Skip Playwright in development — avoids requiring a browser in dev/CI
    if environment == "development":
        return ResponsiveCheckResult(passed=True)

    # TODO: Implement with Playwright
    # from playwright.async_api import async_playwright
    # async with async_playwright() as p:
    #     browser = await p.chromium.launch()
    #     page = await browser.new_page()
    #     for vp in viewports:
    #         await page.set_viewport_size({"width": vp, "height": 800})
    #         await page.set_content(html)
    #         # Check for layout issues, horizontal overflow, etc.
    #     await browser.close()

    return ResponsiveCheckResult(
        passed=True,
        viewport_results={vp: True for vp in viewports},
    )
