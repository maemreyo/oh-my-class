"""Layer 3 — Presentation Contract.

HTML validation (DOCTYPE, no CDN, brand strings) and responsive
viewport checks via Playwright.
"""

from packages.quality.layer3_html.html_validator import HTMLValidator
from packages.quality.layer3_html.responsive_check import check_responsive

__all__ = ["HTMLValidator", "check_responsive"]
