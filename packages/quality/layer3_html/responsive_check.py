"""Responsive check — Playwright viewport tests for HTML output.

Tests rendered HTML at multiple viewport widths (375/768/1280/1920)
to verify responsive behavior. Only runs in staging/production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Default viewports for responsive testing (AGENTS.md §7 Layer 3)
DEFAULT_VIEWPORTS: list[dict[str, int]] = [
    {"width": 375, "height": 812},   # Mobile (iPhone)
    {"width": 768, "height": 1024},   # Tablet (iPad)
    {"width": 1280, "height": 800},   # Laptop
    {"width": 1920, "height": 1080},  # Desktop
]


@dataclass
class ResponsiveCheckResult:
    """Result of responsive viewport testing."""

    passed: bool
    viewport_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


async def check_responsive(
    html: str,
    *,
    viewports: list[dict[str, int]] | None = None,
    skip_in_dev: bool = True,
) -> ResponsiveCheckResult:
    """Test HTML rendering at multiple viewport widths using Playwright.

    Args:
        html: Complete HTML content to test.
        viewports: Custom viewport sizes. Defaults to DEFAULT_VIEWPORTS.
        skip_in_dev: If True, skip in development environment.

    Returns:
        ResponsiveCheckResult with per-viewport results.

    TODO: Implement with Playwright.
    """
    if viewports is None:
        viewports = DEFAULT_VIEWPORTS

    # TODO: Implement Playwright-based responsive testing
    # 1. Create a browser context
    # 2. For each viewport size:
    #    a. Set viewport dimensions
    #    b. Navigate to HTML content (data URI or local file)
    #    c. Check for horizontal overflow
    #    d. Check element visibility
    #    e. Take screenshot (optional)
    # 3. Return results

    return ResponsiveCheckResult(passed=True)
