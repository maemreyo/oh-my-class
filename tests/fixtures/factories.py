from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from tests.fixtures.inverse_thinking import load_fixture


def inverse_thinking_pack_payload(
    fixture_name: str = "english_grammar_present_perfect",
) -> dict[str, Any]:
    fixture = load_fixture(fixture_name)
    return deepcopy(fixture.data["pack"])


def artifact_content_payload(
    artifact_type: Literal["lesson", "worksheet", "quiz", "drill", "recap", "infographic"] = "lesson",
) -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "theme": "default",
        "title": "Inverse thinking sample",
        "sections": [
            {
                "title": "Case file",
                "components": [
                    {
                        "type": "callout",
                        "variant": "note",
                        "title": "Disaster scene",
                        "body": "A student uses the unsafe shortcut before checking the clue.",
                    }
                ],
            }
        ],
        "metadata": {"methodology": "inverse_thinking"},
        "accessibility": {"language": "en", "reading_level": "Grade 5"},
    }


def teaching_pack_payload() -> dict[str, Any]:
    return {
        "run_id": "run-fixture-inverse-thinking",
        "artifacts": [artifact_content_payload("lesson")],
        "metadata": {"source": "shared_fixture_factory"},
    }


def standalone_html_fixture(body: str = "Student-safe content") -> str:
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        "<style>body{font-family:system-ui}</style></head>"
        f"<body><main><p>oh-my-class</p><article>{body}</article></main></body></html>"
    )
