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

from dataclasses import dataclass, field
from typing import Any

from packages.quality.compliance_policy import (
    answer_key_issues,
    check_doctype,
    check_viewport_meta,
    external_asset_issues,
    external_js_issues,
    html_hard_blocks,
    native_radio_issues,
)


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
        hard_blocks, warnings = html_hard_blocks(html)

        return HTMLValidationResult(
            passed=len(hard_blocks) == 0,
            hard_block_violations=hard_blocks,
            warnings=warnings,
            details={"accessibility": [code for code in hard_blocks if code in {"contrast_below_aa", "missing_alt_text", "broken_heading_order", "missing_form_label", "missing_lang", "missing_long_description"}]},
        )

    def check_doctype(self, html: str) -> bool:
        """Check if DOCTYPE declaration is present.

        Args:
            html: HTML content.

        Returns:
            True if DOCTYPE is present.
        """
        return check_doctype(html)

    def validate_external_assets(self, html: str) -> list[str]:
        """Check for any external asset references.

        INVARIANT-04: HTML output MUST NOT contain any http(s):// asset reference.

        Args:
            html: HTML content.

        Returns:
            List of issues found (empty if no external assets).
        """
        return external_asset_issues(html)

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
        return check_viewport_meta(html)

    def check_answer_key_separation(self, html: str) -> list[str]:
        """Verify answer keys are not in student-facing sections.

        Args:
            html: HTML content.

        Returns:
            List of issues (empty if properly separated).
        """
        return answer_key_issues(html)

    def validate_no_native_radio(self, html: str) -> list[str]:
        """Check for native radio inputs visible to student.

        INVARIANT: Student-facing artifacts MUST NOT contain <input type="radio">.
        Use custom CSS-styled elements instead.

        Args:
            html: HTML content.

        Returns:
            List of issues (empty if no native radios found).
        """
        return native_radio_issues(html)

    def validate_no_external_js(self, html: str) -> list[str]:
        """Check for external JavaScript references.

        INVARIANT: No external JS frameworks allowed (React, Vue, etc.).
        Only inline vanilla JS permitted.

        Args:
            html: HTML content.

        Returns:
            List of issues (empty if no external JS found).
        """
        return external_js_issues(html)
