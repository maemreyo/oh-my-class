"""Teaching Pack stage-based orchestration foundation."""

from packages.agents.teaching_pack.stages import StageEnum, TEACHING_PACK_STAGES, TeachingPackStage, stage_number


def build_teaching_pack_graph(*args, **kwargs):
    from packages.agents.teaching_pack.graph import build_teaching_pack_graph as _build_teaching_pack_graph

    return _build_teaching_pack_graph(*args, **kwargs)

__all__ = ["StageEnum", "TEACHING_PACK_STAGES", "TeachingPackStage", "build_teaching_pack_graph", "stage_number"]
