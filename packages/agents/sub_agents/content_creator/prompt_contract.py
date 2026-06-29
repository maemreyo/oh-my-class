from __future__ import annotations

import json
from typing import Any, Final

ACTIVE_ARTIFACT_TYPES: Final[tuple[str, ...]] = (
    "lesson",
    "worksheet",
    "quiz",
    "drill",
    "recap",
    "infographic",
)

COMPONENT_CONTRACT = """Use only existing renderer component JSON shapes. Do not invent CSS classes, inline styles, raw HTML, or markdown.
Allowed component examples inside section.components:
- heading: {"type":"heading","level":2,"text":"..."}
- paragraph: {"type":"paragraph","text":"..."}
- callout: {"type":"callout","variant":"note|warning|tip|alert","title":"...","body":"..."}
- table: {"type":"table","columns":[...],"rows":[[...]],"caption":"..."}
- question_card: {"type":"question_card","id":"q1","text":"...","options":{"A":"...","B":"...","C":"...","D":"..."},"answer":"B","explain":"..."}
- question_list: {"type":"question_list","section_key":"practice","group":"core","title":"...","questions":[question_card,...]}
- flow_step: {"type":"flow_step","steps":[{"time":"5 min","title":"...","body":"..."}]}
- phase_timeline: {"type":"phase_timeline","phases":[{"title":"...","when":"...","goal":"..."}]}
- vocab_cluster: {"type":"vocab_cluster","title":"...","items":[{"word":"...","definition":"...","example":"..."}]}
- roleplay_script: {"type":"roleplay_script","instruction":"...","lines":[{"speaker":"A","text":"..."}]}
- stat_grid: {"type":"stat_grid","stats":[{"label":"...","value":"..."}]}
- concept_map: {"type":"concept_map","nodes":[{"id":"n1","label":"..."}]}
- timeline: {"type":"timeline","events":[{"time":"...","label":"..."}]}
"""

ARTIFACT_RICHNESS = {
    "lesson": "Include at least 4 sections: objectives, direct teaching, guided practice, and closure. Use flow_step or phase_timeline plus at least one callout and one practice component.",
    "worksheet": "Include at least 3 practice sections with 5+ student questions total, including short_answer and one table or callout component for instructions.",
    "quiz": "Include at least 5 question sections or a question_list with 5 question_card items. Put answers/explanations in teacher_only sections or answer fields only, never student body text.",
    "drill": "Include at least 6 progressively harder practice prompts with immediate practice structure; use question_card/question_list where multiple choice is useful.",
    "recap": "Include at least 4 recap items/sections: key idea, common misconception, example, and exit reflection.",
    "infographic": "Include at least 4 visual sections with concise labels, stat_grid/timeline/concept_map/table components where useful, and no external image URLs.",
}


def build_single_artifact_prompt(
    lesson_summary: dict[str, Any],
    research_summary: dict[str, Any],
    artifact_type: str,
    theme: str,
) -> str:
    richness = ARTIFACT_RICHNESS.get(
        artifact_type,
        "Create a rich, complete artifact with multiple student-visible content units.",
    )
    return f"""Generate a single '{artifact_type}' artifact for the following lesson:

Lesson Plan Summary:
{json.dumps(lesson_summary, ensure_ascii=False, indent=2)}

Research Summary:
{json.dumps(research_summary, ensure_ascii=False, indent=2)}

Theme: {theme}

Generate exactly one ArtifactContent JSON object of type '{artifact_type}'.
Do NOT return an array. Return a single JSON object.

Component-first contract:
{COMPONENT_CONTRACT}

Artifact-specific completeness requirement:
{richness}

Required quality bar:
- Use the renderer's existing components/classes by emitting component JSON only.
- Do not output raw HTML, CSS, class names, markdown, CDN URLs, or external image URLs.
- Produce multiple sections/questions/items for a teacher to judge the artifact, not a one-section shell.
- Keep answer keys separate in teacher_only sections or explicit answer fields; never leak answers into student-facing content.
- Support this artifact type without assuming a different artifact type is generated elsewhere.
"""


def retry_single_artifact_prompt(
    base_user_prompt: str,
    artifact_type: str,
    error: BaseException,
    last_content: str | None = None,
) -> str:
    failed_output_section = ""
    if last_content:
        failed_output_section = f"""
Your previous output (which failed validation):
{last_content[:3000]}

"""
    return f"""
{failed_output_section}Previous validation error:
{str(error)[:1200]}

Fix the specific issues above. Return ONLY a single JSON ArtifactContent object of type '{artifact_type}'.
Do not return an array. Do not return markdown or prose. Every component must satisfy its required fields:
- heading: type, level (1|2|3|4), text
- paragraph: type, text
- callout: type, variant (note|warning|tip|alert), body
- question_card: type, id, text, options (dict with A-D keys), answer, explain
- question_list: type, questions (list of question_card), section_key, group, title

{base_user_prompt}
"""
