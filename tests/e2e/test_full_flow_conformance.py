from __future__ import annotations

import pytest

from packages.agents.teaching_pack.stages import TeachingPackStage
from tests.scenarios import SCENARIOS


EXPECTED_STAGE_ORDER = tuple(stage.value for stage in TeachingPackStage)


def test_canonical_scenarios_define_full_flow_invariants() -> None:
    scenario = SCENARIOS[0]

    assert scenario.key == "math_vn"
    assert scenario.invariants.artifact_types == ("lesson", "worksheet")
    assert scenario.invariants.min_bloom_levels >= 2
    assert scenario.invariants.requires_standalone_html is True
    assert scenario.invariants.forbids_answer_key_leakage is True


@pytest.mark.real_llm
@pytest.mark.skip(reason="requires live graph, DB, and 9Router")
async def test_math_vn_full_flow_uses_authoritative_stage_order() -> None:
    assert EXPECTED_STAGE_ORDER == (
        "setup_contract",
        "preplanning_search",
        "planning_blueprint",
        "post_blueprint_research",
        "artifact_workflow",
        "render_quality",
        "teacher_approval",
        "export_finalize",
    )
