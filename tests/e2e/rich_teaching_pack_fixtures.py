from __future__ import annotations

from typing import Any
from typing import Final

JsonObject = dict[str, Any]

ACTIVE_ARTIFACT_TYPES: Final[tuple[str, ...]] = (
    "lesson",
    "worksheet",
    "quiz",
    "drill",
    "recap",
    "infographic",
)


def rich_artifacts() -> list[JsonObject]:
    return [_artifact(artifact_type) for artifact_type in ACTIVE_ARTIFACT_TYPES]


def minimal_shell_artifact() -> JsonObject:
    return {
        "artifact_id": "lesson-minimal",
        "artifact_type": "lesson",
        "theme": "default",
        "title": "Manual Export Lesson Two",
        "sections": [{"title": "Intro", "content": "Equivalent fractions practice."}],
        "metadata": {"subject": "Math", "grade_level": "Grade 5"},
        "accessibility": {"language": "en"},
    }


def _base(artifact_type: str) -> JsonObject:
    return {
        "artifact_id": f"{artifact_type}-rich",
        "artifact_type": artifact_type,
        "theme": "default",
        "title": f"Equivalent Fractions {artifact_type.title()}",
        "metadata": {
            "subject": "Math",
            "grade_level": "Grade 5",
            "summary": "A complete component-driven pack for equivalent fractions.",
            "key_terms": ["equivalent", "fractions", "numerator", "denominator"],
            "learning_objectives": ["Compare equivalent fractions using area models and number lines"],
        },
        "accessibility": {"language": "en"},
    }


def _artifact(artifact_type: str) -> JsonObject:
    match artifact_type:
        case "lesson":
            return {
                **_base("lesson"),
                "sections": [
                    {
                        "id": "targets",
                        "type": "objective",
                        "title": "Learning Targets",
                        "content": "Students compare equivalent fractions using area models and number lines.",
                        "components": [
                            {"type": "callout", "variant": "note", "title": "Teacher move", "body": "Ask learners to justify equal shaded areas."},
                            {"type": "flow_step", "steps": [{"time": "5 min", "title": "Activate", "body": "Compare two fraction strips."}]},
                        ],
                    },
                    {
                        "id": "practice",
                        "title": "Guided Practice",
                        "content": "Use 1/2, 2/4, and 3/6 to compare equivalent fractions with area models and number lines.",
                        "components": [{
                            "type": "question_card",
                            "id": "lq1",
	                            "text": "Which fraction is equivalent to 1/2 on the same area model and number line?",
	                            "options": {"A": "1/3", "B": "2/4", "C": "3/5", "D": "4/5"},
	                            "answer": "B",
	                            "explain": "2/4 covers the same amount as 1/2.",
	                        }],
                    },
                    {
                        "title": "Teacher Notes",
                        "content": "Use this private guide after class.",
                        "teacher_only": True,
                        "answer_key": {"lq1": "B", "rationale": "2/4 covers the same amount as 1/2."},
                    },
                ],
            }
        case "worksheet":
            return {
                **_base("worksheet"),
                "sections": [
                    {"title": "Visual Models", "content": "Shade and compare equivalent fractions with numerator and denominator labels on area models.", "questions": [
                        {"id": "w1", "prompt": "Shade 1/2 and 2/4. What stays the same?", "type": "short_answer"},
                        {"id": "w2", "prompt": "Draw a model for 3/6 that matches 1/2.", "type": "long_answer"},
                    ]},
                    {"title": "Number Line Check", "content": "Place equivalent fractions on one number line and compare their positions.", "questions": [
                        {"id": "w3", "prompt": "Mark 1/2 and 4/8 on the same line.", "type": "short_answer"},
                        {"id": "w4", "prompt": "Explain why both marks overlap.", "type": "short_answer"},
                    ]},
                    {"title": "Teacher Notes", "content": "Private suggested responses stay out of student HTML.", "teacher_only": True, "answer_key": {"w1": "The shaded amount stays the same."}},
                ],
            }
        case "quiz":
            return {**_base("quiz"), "sections": _question_sections("q", count=5)}
        case "drill":
            return {**_base("drill"), "sections": _question_sections("d", count=6)}
        case "recap":
            return {
                **_base("recap"),
                "sections": [
                    {"title": "Same Value", "content": "Equivalent fractions name the same amount when students compare area models."},
                    {"title": "Area Models", "content": "Equal shaded regions prove equivalent fractions before shortcuts."},
                    {"title": "Number Lines", "content": "Equivalent fractions land on the same number line point."},
                    {"title": "Exit Reflection", "content": "Write one equivalent pair and compare it using a model."},
                ],
            }
        case "infographic":
            return {
                **_base("infographic"),
                "sections": [
                    {"title": "Equal Value", "content": "Equivalent fractions can land on the same number line point."},
                    {"title": "Area Model", "content": "1/2, 2/4, and 3/6 show the same area model amount.", "items": [{"label": "Area", "value": "same shaded amount"}]},
                    {"title": "Compare Strategy", "content": "Compare numerator and denominator changes only after checking a model."},
                    {"title": "Check", "content": "Use area models and number lines before applying a shortcut."},
                ],
            }
        case unreachable:
            raise ValueError(f"unsupported active artifact type: {unreachable}")


def _question_sections(prefix: str, *, count: int) -> list[JsonObject]:
    return [
        {
            "id": f"{prefix}{index}",
            "content": f"Which equivalent fraction matches 1/2 when the numerator and denominator are scaled on an area model and number line in item {index}?",
	            "options": {"A": "1/3", "B": "2/4", "C": "3/5", "D": "4/5"},
	            "answer": "B",
	            "explain": "2/4 is equivalent to 1/2 because numerator and denominator are both doubled.",
	            "type": "question_card",
        }
        for index in range(1, count + 1)
    ] + [{
        "title": "Teacher Notes",
        "content": "Private scoring guidance stays out of the student-facing artifact.",
        "teacher_only": True,
        "answer_key": {f"{prefix}1": "B"},
    }]
