from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.schema_codegen_config import MODELS

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class BoundaryModelUse:
    module_path: str
    importer: str
    reason: str


BOUNDARY_MODEL_USES: tuple[BoundaryModelUse, ...] = (
    BoundaryModelUse(
        "common.contracts.artifact",
        "packages/agents/teaching_pack/quality.py",
        "artifact content crosses from agents to renderer and gateway quality routes",
    ),
    BoundaryModelUse(
        "common.contracts.artifact_workflow",
        "packages/agents/teaching_pack/quality_runtime.py",
        "artifact workflow state is persisted and surfaced across gateway/runtime seams",
    ),
    BoundaryModelUse(
        "common.contracts.errors",
        "services/gateway/middleware/error_handler.py",
        "gateway HTTP error envelopes are frontend API responses",
    ),
    BoundaryModelUse(
        "common.contracts.judge_output",
        "packages/quality/layer4_judge/judge_interface.py",
        "judge outputs cross the quality package and gateway boundary",
    ),
    BoundaryModelUse(
        "common.contracts.lesson_plan",
        "packages/agents/sub_agents/planner/nodes.py",
        "planner output is a teacher-visible generated artifact contract",
    ),
    BoundaryModelUse(
        "common.contracts.lesson_sequence",
        "common/contracts/unit_view.py",
        "unit sequence is embedded in generated unit API views",
    ),
    BoundaryModelUse(
        "common.contracts.quality",
        "services/gateway/quality_workflow.py",
        "quality reports and healing decisions cross gateway/runtime seams",
    ),
    BoundaryModelUse(
        "common.contracts.research_brief",
        "services/gateway/research_engine.py",
        "research briefs feed teacher-confirmed search and artifact generation seams",
    ),
    BoundaryModelUse(
        "common.contracts.run_contract",
        "services/gateway/run_contract_setup.py",
        "run contracts are persisted, resumed, and exposed to frontend confirmation flows",
    ),
    BoundaryModelUse(
        "common.contracts.unit_view",
        "common/contracts/__init__.py",
        "unit view and SSE event payload models are frontend API contracts",
    ),
)


def test_boundary_common_contract_models_are_codegen_registered() -> None:
    missing = sorted(
        use.module_path
        for use in BOUNDARY_MODEL_USES
        if use.module_path not in MODELS
    )

    assert missing == []


def test_boundary_inventory_references_existing_importers() -> None:
    missing_importers = sorted(
        f"{use.module_path} -> {use.importer}"
        for use in BOUNDARY_MODEL_USES
        if not (PROJECT_ROOT / use.importer).exists()
    )

    assert missing_importers == []
