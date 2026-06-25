"""HTML structural validator for artifact content."""
from __future__ import annotations

import re
from typing import Any

DOCTYPE_PATTERN = re.compile(r"<!DOCTYPE\s+html", re.IGNORECASE)
EXTERNAL_ASSET_PATTERN = re.compile(r'(?:src|href)=["\']https?://', re.IGNORECASE)


def validate_html(html: str, *, block_external_assets: bool = True, block_missing_doctype: bool = True) -> dict[str, Any]:  # noqa: E501
    """Validate HTML artifact for structural issues.

    Returns:
        {"passed": bool, "errors": list[str], "warnings": list[str]}
    """
    errors = []
    warnings = []

    if block_missing_doctype and not DOCTYPE_PATTERN.search(html):
        errors.append("Missing <!DOCTYPE html> declaration")

    if block_external_assets and EXTERNAL_ASSET_PATTERN.search(html):
        errors.append("External assets detected (src/href with http:// or https://)")

    # Check for unclosed common tags
    for tag in ["div", "p", "ul", "ol", "table"]:
        opens = len(re.findall(rf"<{tag}[^>]*>", html, re.IGNORECASE))
        closes = len(re.findall(rf"</{tag}>", html, re.IGNORECASE))
        if opens > closes:
            warnings.append(f"Possibly unclosed <{tag}> tags ({opens} open, {closes} close)")

    return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings}
