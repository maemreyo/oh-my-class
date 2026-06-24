"""HTML-specific healing — DOCTYPE injection, unclosed tag repair."""
from __future__ import annotations
import re

DOCTYPE_HEADER = "<!DOCTYPE html>\n"


def _inject_doctype(html: str) -> str:
    """Inject DOCTYPE if missing."""
    if not re.search(r"<!DOCTYPE\s+html", html, re.IGNORECASE):
        return DOCTYPE_HEADER + html
    return html


def _remove_external_assets(html: str) -> str:
    """Replace external asset URLs with empty strings."""
    return re.sub(
        r'((?:src|href)=["\'])https?://[^"\']*(["\'])',
        r"\1\2",
        html,
        flags=re.IGNORECASE,
    )


def validate_and_heal(html: str, max_attempts: int = 3) -> dict:
    """Attempt to heal common HTML issues.

    Returns:
        {"healed": bool, "html": str, "changes": list[str], "attempts": int}
    """
    changes = []
    healed_html = html

    for attempt in range(1, max_attempts + 1):
        original = healed_html

        healed_html = _inject_doctype(healed_html)
        if healed_html != original:
            changes.append("injected DOCTYPE")
            original = healed_html

        healed_html = _remove_external_assets(healed_html)
        if healed_html != original:
            changes.append("removed external asset URLs")

        if healed_html == html and attempt == 1:
            # No changes on first pass = nothing to heal
            break

    return {
        "healed": len(changes) > 0,
        "html": healed_html,
        "changes": changes,
        "attempts": min(max_attempts, 1 if not changes else max_attempts),
    }
