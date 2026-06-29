from __future__ import annotations

from hashlib import sha256

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


def build_snapshot(run_id: str, artifact: JsonObject) -> JsonObject:
    artifact_id = str(artifact["artifact_id"])
    artifact_type = str(artifact["artifact_type"])
    html = render_teacher_html(artifact)
    return {
        "snapshot_id": f"snap-{_stable_id(run_id, artifact_id)}",
        "run_id": run_id,
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "content_json": artifact,
        "rendered_html": html,
        "student_rendered_html": render_student_html(artifact),
        "renderer_version": "pipeline-v2-python",
        "template_version": "pipeline-v2-minimal",
        "theme_version": "default",
    }


def render_teacher_html(artifact: JsonObject) -> str:
    title = str(artifact["title"])
    section_html = _sections_html(artifact, include_teacher_only=True)
    return (
        "<!DOCTYPE html>"
        "<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{_escape(title)}</title>"
        "<style>body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:2rem;line-height:1.5}"
        ".brand{font-weight:700}.teacher-only{border-top:1px solid #ddd;margin-top:2rem;padding-top:1rem}</style>"
        "</head><body>"
        "<header class=\"brand\">oh-my-class</header>"
        f"<main><h1>{_escape(title)}</h1>{section_html}</main>"
        "<section class=\"teacher-only\" data-teacher-only=\"true\"><h2>Teacher only</h2><p>Answer key is separated here.</p></section>"
        "</body></html>"
    )


def render_student_html(artifact: JsonObject) -> str:
    title = str(artifact["title"])
    section_html = _sections_html(artifact, include_teacher_only=False)
    return (
        "<!DOCTYPE html>"
        "<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{_escape(title)}</title>"
        "<style>body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:2rem;line-height:1.5}</style>"
        "</head><body><header>oh-my-class</header>"
        f"<main><h1>{_escape(title)}</h1>{section_html}</main></body></html>"
    )


def _sections_html(artifact: JsonObject, *, include_teacher_only: bool) -> str:
    sections = artifact.get("sections", [])
    if not isinstance(sections, list):
        return ""
    return "".join(
        _section_html(section, include_teacher_only=include_teacher_only)
        for section in sections
        if isinstance(section, dict) and (include_teacher_only or section.get("teacher_only") is not True)
    )


def _section_html(section: JsonObject, *, include_teacher_only: bool) -> str:
    heading = str(section.get("heading") or section.get("title") or "Section")
    body = str(section.get("body") or section.get("content") or section.get("text") or "")
    teacher_only = include_teacher_only and section.get("teacher_only") is True
    attr = ' data-teacher-only="true"' if teacher_only else ""
    return f"<section{attr}><h2>{_escape(heading)}</h2><p>{_escape(body)}</p></section>"


def _stable_id(run_id: str, value: str) -> str:
    return sha256(f"{run_id}:{value}".encode()).hexdigest()[:24]


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
