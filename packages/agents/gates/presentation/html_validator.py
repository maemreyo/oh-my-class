"""HTML structural validator for artifact content."""
from __future__ import annotations

import re
from typing import Any

from packages.quality.compliance_policy import check_doctype, external_asset_issues


def validate_html(html: str) -> dict[str, Any]:
    """Validate HTML artifact for structural issues.

    Returns:
        {"passed": bool, "errors": list[str], "warnings": list[str]}
    """
    errors = []
    warnings = []

    if not check_doctype(html):
        errors.append("Missing <!DOCTYPE html> declaration")

    if external_asset_issues(html):
        errors.append("External assets detected (src/href with http:// or https://)")

    # Check for unclosed common tags
    for tag in ["div", "p", "ul", "ol", "table"]:
        opens = len(re.findall(rf"<{tag}[^>]*>", html, re.IGNORECASE))
        closes = len(re.findall(rf"</{tag}>", html, re.IGNORECASE))
        if opens > closes:
            warnings.append(f"Possibly unclosed <{tag}> tags ({opens} open, {closes} close)")

    return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings}
