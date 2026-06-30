from __future__ import annotations

from packages.agents.teaching_pack.nodes import make_stage_node
from packages.agents.teaching_pack.stages import TeachingPackStage


async def test_unit_prep_locks_theme_research_and_persona() -> None:
    node = make_stage_node(TeachingPackStage.UNIT_PREP)

    result = await node({
        "run_id": "run-unit-context",
        "contract": {
            "theme": "ocean",
            "persona_snapshot": {"grade": "Grade 5"},
        },
        "research_brief": {"sources": [{"title": "shared"}]},
    })

    assert result["unit_context"] == {
        "locked_theme": "ocean",
        "shared_research": {"sources": [{"title": "shared"}]},
        "persona_snapshot": {"grade": "Grade 5"},
    }
