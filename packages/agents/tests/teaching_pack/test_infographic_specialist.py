from __future__ import annotations

import pytest

from packages.agents.teaching_pack.specialists.infographic_specialist import (
    NoInfographicContextError,
    generate_infographic_artifact,
)
from packages.quality.layer1_schema.component_gate import validate_component_minimums


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Fractions",
        "subject": "Math",
        "grade_level": "Grade 5",
        "locale": "en",
        "learning_objectives": [{"description": "Identify equivalent fractions."}],
    }


def test_infographic_is_offline_safe_and_accessibly_described() -> None:
    artifact = generate_infographic_artifact(_lesson_plan(), {"sources": []})

    assert validate_component_minimums(artifact) == []
    assert artifact["accessibility"]["alt_texts"] == ["Identify equivalent fractions."]
    assert artifact["metadata"]["infographic_scorecard"]["offline_safety"] == 1.0


def test_infographic_fails_closed_without_objectives() -> None:
    with pytest.raises(NoInfographicContextError):
        generate_infographic_artifact({"topic": "Empty"}, {"sources": []})


def test_grounded_finding_is_preserved_without_remote_asset_url() -> None:
    artifact = generate_infographic_artifact(_lesson_plan(), {
        "sources": [{"title": "Fractions Guide", "excerpt": "Equivalent fractions represent the same value."}],
    })

    assert artifact["sections"][1]["content"] == "Equivalent fractions represent the same value."
    assert "https://" not in str(artifact)
