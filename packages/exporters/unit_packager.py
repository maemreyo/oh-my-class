"""UnitPackager — compose approved session exports into a unit bundle (td-017).

Packaging is orthogonal to ExportFormat — no new enum values are introduced.
Generated lazily on demand (POST /units/{id}/export trigger).

HTML bundle structure:
  cover → sequence/prerequisite overview → table of contents → linked sessions.

Assessment bundle:
  zip of per-session files + unit_manifest.json.
"""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SessionExportResult:
    session_id: str
    session_index: int
    title: str
    html_content: str | None
    is_approved: bool
    is_included: bool


@dataclass
class UnitBundleResult:
    parent_run_id: str
    topic: str
    total_sessions: int
    included_sessions: int
    omitted_sessions: list[dict]  # [{"session_id": ..., "status": ..., "title": ...}]
    html_bundle: str | None
    assessment_zip: bytes | None


# ---------------------------------------------------------------------------
# HTML fragment helpers
# ---------------------------------------------------------------------------


def _html_cover(topic: str, total: int, included: int, theme: str) -> str:
    partial_note = ""
    if included < total:
        partial_note = (
            f'<p class="unit-partial-warning">'
            f"⚠️ {included}/{total} approved sessions included in this bundle."
            f"</p>"
        )
    return (
        f'<section class="unit-cover" data-theme="{theme}">'
        f"<h1>{topic}</h1>"
        f'<p class="unit-meta">{included} session(s) · Theme: {theme}</p>'
        f"{partial_note}"
        f"</section>\n"
    )


def _html_toc(sessions: list[SessionExportResult]) -> str:
    items = "\n".join(
        f'<li><a href="#session-{s.session_index}">{s.session_index}. {s.title}</a></li>'
        for s in sessions
        if s.is_included
    )
    return f'<nav class="unit-toc"><h2>Table of Contents</h2><ol>{items}</ol></nav>\n'


def _html_sequence_overview(sequence_data: dict) -> str:
    sessions = sequence_data.get("sessions", [])
    if not sessions:
        return ""
    rows = ""
    for s in sessions:
        prereqs = ", ".join(s.get("prerequisite_sessions", [])) or "—"
        rows += (
            f"<tr>"
            f"<td>{s.get('order_index', '?')}</td>"
            f"<td>{s.get('title', '')}</td>"
            f"<td>{s.get('bloom_level_primary', '')}</td>"
            f"<td>{s.get('methodology_primary', '')}</td>"
            f"<td>{prereqs}</td>"
            f"</tr>\n"
        )
    return (
        '<section class="unit-sequence-overview">'
        "<h2>Session Sequence</h2>"
        '<table><thead><tr><th>#</th><th>Title</th><th>Bloom</th><th>Methodology</th><th>Prerequisites</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
        "</section>\n"
    )


# ---------------------------------------------------------------------------
# UnitPackager
# ---------------------------------------------------------------------------


class UnitPackager:
    """Composes a unit bundle from approved session exports."""

    def __init__(
        self,
        session_results: list[SessionExportResult],
        sequence_data: dict,
        theme: str = "default",
    ) -> None:
        self._session_results = session_results
        self._sequence_data = sequence_data
        self._theme = sequence_data.get("theme", theme) or theme

    @property
    def _included(self) -> list[SessionExportResult]:
        return [s for s in self._session_results if s.is_included and s.is_approved]

    @property
    def _omitted(self) -> list[dict]:
        return [
            {"session_id": s.session_id, "title": s.title, "status": "omitted"}
            for s in self._session_results
            if not s.is_included or not s.is_approved
        ]

    def build_html_bundle(self) -> str:
        """Compose all approved sessions into a single HTML document."""
        included = self._included
        total = len(self._session_results)
        topic = self._sequence_data.get("topic", "Unit")

        parts: list[str] = [
            "<!DOCTYPE html>\n"
            f'<html lang="vi">\n<head><meta charset="UTF-8">'
            f'<title>{topic}</title>'
            f'<meta name="unit-theme" content="{self._theme}">'
            "</head>\n<body>\n",
            _html_cover(topic, total, len(included), self._theme),
            _html_sequence_overview(self._sequence_data),
            _html_toc(included),
        ]

        for sess in sorted(included, key=lambda s: s.session_index):
            parts.append(
                f'<section id="session-{sess.session_index}" class="unit-session">\n'
                f"<h2>{sess.session_index}. {sess.title}</h2>\n"
                + (sess.html_content or f"<p>[Session {sess.session_index} content not yet rendered]</p>")
                + "\n</section>\n"
            )

        parts.append("</body>\n</html>")
        return "".join(parts)

    def build_assessment_zip(self, format_name: str = "gift") -> bytes:
        """Produce a zip of per-session files + unit_manifest.json."""
        buf = io.BytesIO()
        included = self._included
        topic = self._sequence_data.get("topic", "Unit")

        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for sess in included:
                filename = f"session_{sess.session_index:02d}_{sess.session_id}.{format_name}"
                content = (
                    sess.html_content or f"// Session {sess.session_index}: {sess.title}\n// Content pending"
                )
                zf.writestr(filename, content)

            manifest = {
                "unit_id": self._sequence_data.get("parent_run_id", ""),
                "topic": topic,
                "total_sessions": len(self._session_results),
                "included": [
                    {"session_id": s.session_id, "title": s.title, "index": s.session_index}
                    for s in included
                ],
                "omitted": self._omitted,
                "theme": self._theme,
                "format": format_name,
            }
            zf.writestr("unit_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        return buf.getvalue()

    def build_bundle(self) -> UnitBundleResult:
        """Build both HTML and assessment zip bundles."""
        return UnitBundleResult(
            parent_run_id=self._sequence_data.get("parent_run_id", ""),
            topic=self._sequence_data.get("topic", "Unit"),
            total_sessions=len(self._session_results),
            included_sessions=len(self._included),
            omitted_sessions=self._omitted,
            html_bundle=self.build_html_bundle(),
            assessment_zip=self.build_assessment_zip(),
        )
