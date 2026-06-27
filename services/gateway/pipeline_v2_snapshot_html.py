"""HTML validation and rendering utilities for snapshot processing.

Standalone HTML checks, asset detection, and student preview rendering.
"""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.gateway.pipeline_v2_types import JsonObject, JsonValue


_CSS_EXTERNAL_ASSET_PATTERN = re.compile(
    r"(?:@import\s+url\(|url\()\s*['\"]?(?:https?://|//)",
    re.IGNORECASE,
)


class StandaloneHtmlAssetParser(HTMLParser):
    """Parse HTML and detect external asset references (script src, link href, etc.)."""

    def __init__(self) -> None:
        super().__init__()
        self.has_external_asset = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._tag_has_external_reference(tag, attrs):
            self.has_external_asset = True

    def _tag_has_external_reference(self, tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        lowered_tag = tag.lower()
        for name, value in attrs:
            if value is None:
                continue
            lowered_name = name.lower()
            if lowered_tag == "link" and lowered_name == "href":
                return not _is_inline_reference_url(value)
            if lowered_tag == "script" and lowered_name == "src":
                return True
            if lowered_name in {"src", "href"} and _is_external_asset_url(value):
                return True
        return False


def _is_external_asset_url(value: str) -> bool:
    """Check if a URL is external (http://, https://, //)."""
    stripped = value.strip().lower()
    return stripped.startswith(("http://", "https://", "//"))


def _is_inline_reference_url(value: str) -> bool:
    """Check if a URL is inline (data: URI or fragment #)."""
    stripped = value.strip().lower()
    return stripped.startswith(("data:", "#"))


def is_standalone_html(rendered_html: str) -> bool:
    """Validate that HTML is standalone (no external assets, has DOCTYPE).

    Returns True if:
    - Contains <!DOCTYPE html>
    - Has no external script src or link href
    - Has no external CSS @import or url() references
    """
    lowered = rendered_html.lower()
    has_doctype = "<!doctype html" in lowered
    parser = StandaloneHtmlAssetParser()
    parser.feed(rendered_html)
    has_css_external_asset = _CSS_EXTERNAL_ASSET_PATTERN.search(rendered_html) is not None
    return has_doctype and not parser.has_external_asset and not has_css_external_asset


def render_student_preview_html(content_json: JsonObject) -> str:
    """Render a minimal HTML preview from content JSON (student-facing only).

    Excludes sections marked with teacher_only=true.
    Returns standalone HTML with title and sections.
    """
    title = escape(str(content_json.get("title", "oh-my-class preview")))
    sections = content_json.get("sections", [])
    bodies: list[str] = []
    if isinstance(sections, list):
        for section in sections:
            if isinstance(section, dict) and section.get("teacher_only") is not True:
                bodies.append(f"<section>{_safe_section_text(section)}</section>")
    body = "".join(bodies) or "<section>oh-my-class preview</section>"
    return f"<!DOCTYPE html><html><body><h1>{title}</h1>{body}</body></html>"


def _safe_section_text(section: dict[str, JsonValue]) -> str:
    """Extract and escape text from a section dict, excluding teacher_only key."""
    values = [escape(str(value)) for key, value in section.items() if key != "teacher_only"]
    return " ".join(values)
