from __future__ import annotations

from typing import Literal

from common.contracts.inverse_thinking import InverseThinkingPack

ArtifactType = Literal["lesson", "worksheet", "quiz", "drill", "teacher_only"]
Frame = Literal["detective_case", "neutral"]


def render_release_fixture_html(
    payload: InverseThinkingPack | dict,
    *,
    artifact_type: ArtifactType,
    frame: Frame = "detective_case",
) -> str:
    pack = InverseThinkingPack.model_validate(payload)
    body = _teacher_body(pack) if artifact_type == "teacher_only" else _student_body(pack, artifact_type)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Inverse Thinking — oh-my-class</title>
  <style>:root{{--paper:#fffaf0;--ink:#1f2937}}body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--paper)}}.case-file,.summary-wrap,.student-challenge,.teacher-only{{border:1px solid #d7c9aa;border-radius:16px;padding:16px;margin:16px 0}}.frame-neutral{{--paper:#fff}}@media print{{.case-file{{page-break-inside:avoid}}}}</style>
</head>
<body class="inverse-thinking frame-{frame.replace('_case', '') if frame == 'detective_case' else 'neutral'}">
  <header><strong>oh-my-class</strong></header>
  <main>{body}</main>
</body>
</html>"""


def _student_body(pack: InverseThinkingPack, artifact_type: ArtifactType) -> str:
    cases = "".join(
        f"""<article class="case-file" data-case-id="{case.id}">
  <h2>{case.title}</h2>
  <section><h3>Scene</h3><p>{case.disaster}</p></section>
  <section><h3>Key clues</h3><p>{'; '.join(case.key_clues)}</p></section>
  <section><h3>Safe zone</h3><p>{case.safe_zone}</p></section>
  <section><h3>Filing note</h3><p>{case.filing_note}</p></section>
  <section class="student-challenge"><h3>Student challenge</h3><p>{case.student_task}</p></section>
</article>"""
        for case in pack.cases
    )
    summary = "".join(
        f"<tr><td>{row.case_id}</td><td>{row.trap}</td><td>{row.clue}</td><td>{row.safe_rule}</td></tr>"
        for row in pack.summary_table
    )
    practice_label = {
        "worksheet": "Evidence worksheet practice",
        "quiz": "Clue quiz practice",
        "drill": "Repair drill practice",
    }.get(artifact_type, "Inverse Thinking practice")
    practice = "" if artifact_type == "lesson" else f"<section class=\"student-challenge\"><h2>{practice_label}</h2><p>Use the same case flow on a new unsafe example.</p></section>"
    return f"{cases}<section class=\"summary-wrap\"><h2>Summary table</h2><table>{summary}</table></section>{practice}"


def _teacher_body(pack: InverseThinkingPack) -> str:
    return f"<section class=\"teacher-only\"><h2>Teacher-only key</h2><p>{pack.teacher_only.rationale}</p><p>{pack.teacher_only.answer_key}</p></section>"
