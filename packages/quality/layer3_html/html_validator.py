"""HTML validator — presentation contract checks for standalone HTML output.

Validates that generated HTML meets all presentation requirements:
- DOCTYPE present
- No external assets (CDN links, external images, @import url(http...))
- Brand string "oh-my-class" present
- Viewport meta present
- Answer key separation
- No native radio inputs visible to student
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Patterns that indicate external assets (CRITICAL violations)
EXTERNAL_ASSET_PATTERNS: list[str] = [
    r'href="https?://',
    r"href='https?://",
    r'src="https?://',
    r"src='https?://",
    r'@import\s+url\(["\']?https?://',
    r'background-image:\s*url\(["\']?https?://',
]

# Hard block codes (auto-fail regardless of score)
HARD_BLOCKS: list[str] = [
    "missing_doctype",
    "external_assets",
    "answer_key_leakage",
    "native_radio_inputs",
    "unmanaged_js_runtime",
    "missing_brand_string",
]


@dataclass
class HTMLValidationResult:
    """Result of HTML presentation contract validation."""

    passed: bool
    hard_block_violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class HTMLValidator:
    """Validates HTML output against the presentation contract.

    Usage:
        validator = HTMLValidator()
        result = validator.validate(html_content)
    """

    def validate(self, html: str) -> HTMLValidationResult:
        """Run all HTML validation checks.

        Args:
            html: Complete HTML content to validate.

        Returns:
            HTMLValidationResult with pass/fail and issues.
        """
        hard_blocks: list[str] = []
        warnings: list[str] = []

        # Check DOCTYPE
        if not self.check_doctype(html):
            hard_blocks.append("missing_doctype")

        # Check external assets
        external_issues = self.validate_external_assets(html)
        if external_issues:
            hard_blocks.append("external_assets")

        # Check brand string
        if not self.check_brand_string(html):
            hard_blocks.append("missing_brand_string")

        # Check viewport meta
        if not self.check_viewport_meta(html):
            warnings.append("missing_viewport_meta")

        # Check native radio inputs
        radio_issues = self.validate_no_native_radio(html)
        if radio_issues:
            hard_blocks.append("native_radio_inputs")

        # Check external JS
        js_issues = self.validate_no_external_js(html)
        if js_issues:
            hard_blocks.append("unmanaged_js_runtime")

        # Check answer key separation
        answer_issues = self.check_answer_key_separation(html)
        if answer_issues:
            hard_blocks.append("answer_key_leakage")

        return HTMLValidationResult(
            passed=len(hard_blocks) == 0,
            hard_block_violations=hard_blocks,
            warnings=warnings,
        )

    def check_doctype(self, html: str) -> bool:
        """Check if DOCTYPE declaration is present.

        Args:
            html: HTML content.

        Returns:
            True if DOCTYPE is present.
        """
        return html.strip().upper().startswith("<!DOCTYPE HTML>")

    def validate_external_assets(self, html: str) -> list[str]:
        """Check for any external asset references.

        INVARIANT-04: HTML output MUST NOT contain any http(s):// asset reference.

        Args:
            html: HTML content.

        Returns:
            List of issues found (empty if no external assets).
        """
        issues: list[str] = []
        for pattern in EXTERNAL_ASSET_PATTERNS:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                issues.append(f"External asset reference found: {pattern}")
        return issues

    def check_brand_string(self, html: str) -> bool:
        """Check if brand string is present.

        Args:
            html: HTML content.

        Returns:
            True if 'oh-my-class' is found in the HTML.
        """
        return "oh-my-class" in html.lower()

    def check_viewport_meta(self, html: str) -> bool:
        """Check if viewport meta tag is present.

        Args:
            html: HTML content.

        Returns:
            True if viewport meta is present.
        """
        return bool(re.search(r'<meta\s+name=["\']viewport["\']', html, re.IGNORECASE))

    def check_answer_key_separation(self, html: str) -> list[str]:
        """Verify answer keys are not in student-facing sections.

        Args:
            html: HTML content.

        Returns:
            List of issues (empty if properly separated).
        """
        issues: list[str] = []
        answer_patterns = [
            r'correct\s+answer',
            r'answer\s*:',
            r'solution\s*:',
            r'answer\s+key',
        ]
        for pattern in answer_patterns:
            if re.findall(pattern, html, re.IGNORECASE):
                issues.append(f"Answer key pattern found: '{pattern}'")
        return issues

    def validate_no_native_radio(self, html: str) -> list[str]:
        """Check for native radio inputs visible to student.

        INVARIANT: Student-facing artifacts MUST NOT contain <input type="radio">.
        Use custom CSS-styled elements instead.

        Args:
            html: HTML content.

        Returns:
            List of issues (empty if no native radios found).
        """
        issues: list[str] = []
        matches = re.findall(r'<input\s+[^>]*type=["\']radio["\']', html, re.IGNORECASE)
        if matches:
            issues.append(f"Native radio inputs found: {len(matches)} instances")
        return issues

    def validate_no_external_js(self, html: str) -> list[str]:
        """Check for external JavaScript references.

        INVARIANT: No external JS frameworks allowed (React, Vue, etc.).
        Only inline vanilla JS permitted.

        Args:
            html: HTML content.

        Returns:
            List of issues (empty if no external JS found).
        """
        issues: list[str] = []

        matches = re.findall(r'<script\s+[^>]*src=["\']https?://', html, re.IGNORECASE)
        if matches:
            issues.append(f"External script references found: {len(matches)} instances")

        cdn_patterns = [
            ("cdn.tailwindcss.com", r'cdn\.tailwindcss\.com'),
            ("cdnjs.cloudflare.com", r'cdnjs\.cloudflare\.com'),
            ("cdn.jsdelivr.net", r'cdn\.jsdelivr\.net'),
            ("unpkg.com", r'unpkg\.com'),
        ]
        for display, pattern in cdn_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                issues.append(f"CDN framework detected: {display}")

        return issues
