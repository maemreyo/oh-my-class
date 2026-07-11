from __future__ import annotations

import ast
import inspect
import json
import sys
from pathlib import Path
from typing import Final, TypedDict, get_args

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
MANIFEST_PATH: Final[Path] = PROJECT_ROOT / "docs" / "system" / "architecture.manifest.json"
MIGRATIONS_PATH: Final[Path] = PROJECT_ROOT / "services" / "gateway" / "alembic" / "versions"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.architecture_surfaces import ArchitectureSurfaces, collect_architecture_surfaces


class StageManifest(TypedDict):
    enum: list[str]
    canonical: list[str]


class RouterManifest(TypedDict):
    name: str
    prefix: str
    tags: list[str]


class ExportFormatManifest(TypedDict):
    all: list[str]
    supported: list[str]
    unsupported: list[str]


class ModelManifest(TypedDict):
    llm_base_url: str
    assignments: dict[str, str]


class GatesManifest(TypedDict):
    fast_lane_eligible: list[str]
    fast_lane_excluded: list[str]
    fast_lane_threshold_default: float | None


class WiringManifest(TypedDict):
    quality_gate_injected: bool
    middleware_runner_active: bool
    lead_agent_present: bool
    legacy_graph_present: bool
    teaching_pack_graph_builder_present: bool
    artifact_send_default_enabled: bool
    artifact_send_worker_node_present: bool
    artifact_send_reducer_channels_present: bool
    artifact_send_rollback_flag: str


class ArchitectureManifest(TypedDict):
    stages: StageManifest
    routers: list[RouterManifest]
    run_statuses: list[str]
    gate_names: list[str]
    gates: GatesManifest
    migration_count: int
    export_formats: ExportFormatManifest
    models: ModelManifest
    wiring: WiringManifest
    surfaces: ArchitectureSurfaces


def build_manifest() -> ArchitectureManifest:
    from common.contracts.run_contract import ExportFormat
    from packages.agents.config.gate_config import GateConfig
    from packages.agents.config.models import ModelAssignments
    from packages.llm_client.config import LLMClientConfig
    from packages.agents.teaching_pack.exporters import ExporterRegistry
    from packages.agents.teaching_pack.gate_trust import (
        _FAST_LANE_ELIGIBLE_GATES,
        _FAST_LANE_EXCLUDED_GATES,
    )
    from packages.agents.teaching_pack.stages import TEACHING_PACK_STAGES, TeachingPackStage
    from services.gateway.models import RunStatus
    from services.gateway.teaching_pack_gate_registry import TeachingPackGateName

    export_formats = list(get_args(ExportFormat))
    registry = ExporterRegistry.default()
    return {
        "stages": {
            "enum": [stage.value for stage in TeachingPackStage],
            "canonical": [stage.value for stage in TEACHING_PACK_STAGES],
        },
        "routers": _http_routes(),
        "run_statuses": [status.value for status in RunStatus],
        "gate_names": [gate.value for gate in TeachingPackGateName],
        "gates": {
            "fast_lane_eligible": sorted(_FAST_LANE_ELIGIBLE_GATES),
            "fast_lane_excluded": sorted(_FAST_LANE_EXCLUDED_GATES),
            "fast_lane_threshold_default": GateConfig().fast_lane_threshold,
        },
        "migration_count": len([
            path for path in MIGRATIONS_PATH.glob("*.py") if path.name != "__init__.py"
        ]),
        "export_formats": {
            "all": export_formats,
            "supported": [value for value in export_formats if registry.supports(value)],
            "unsupported": [
                value for value in export_formats if registry.is_explicitly_unsupported(value)
            ],
        },
        "models": {
            "llm_base_url": LLMClientConfig().base_url,
            "assignments": {
                name: getattr(ModelAssignments(), name)
                for name in sorted(ModelAssignments.model_fields)
            },
        },
        "wiring": _wiring_booleans(),
        "surfaces": collect_architecture_surfaces(PROJECT_ROOT),
    }


def write_manifest(path: Path = MANIFEST_PATH) -> None:
    path.write_text(
        json.dumps(build_manifest(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _http_routes() -> list[RouterManifest]:
    main_path = PROJECT_ROOT / "services" / "gateway" / "main.py"
    module = ast.parse(main_path.read_text(encoding="utf-8"))
    routers: list[RouterManifest] = []
    for node in ast.walk(module):
        match node:
            case ast.Call(func=ast.Attribute(value=ast.Name(id="app"), attr="include_router")):
                routers.append(_router_manifest(node))
            case _:
                continue
    return sorted(routers, key=lambda item: (item["prefix"], item["name"]))


def _router_manifest(call: ast.Call) -> RouterManifest:
    return {
        "name": _router_name(call),
        "prefix": _string_keyword(call, "prefix"),
        "tags": _string_list_keyword(call, "tags"),
    }


def _router_name(call: ast.Call) -> str:
    if not call.args:
        return ""
    match call.args[0]:
        case ast.Attribute(value=ast.Name(id=name), attr="router"):
            return name
        case ast.Name(id=name):
            return name
        case _:
            return ""


def _string_keyword(call: ast.Call, key: str) -> str:
    for keyword in call.keywords:
        if keyword.arg == key:
            match keyword.value:
                case ast.Constant(value=str(value)):
                    return value
                case _:
                    return ""
    return ""


def _string_list_keyword(call: ast.Call, key: str) -> list[str]:
    for keyword in call.keywords:
        if keyword.arg == key:
            match keyword.value:
                case ast.List(elts=elts):
                    return [value for item in elts if isinstance(item, ast.Constant) and isinstance((value := item.value), str)]
                case _:
                    return []
    return []


def _wiring_booleans() -> WiringManifest:
    from packages.agents.teaching_pack.artifact_fanout import GENERATE_ONE_ARTIFACT_NODE
    from packages.agents.teaching_pack.features import artifact_send_fanout_v1_enabled
    from packages.agents.teaching_pack.graph import build_teaching_pack_graph
    from packages.agents.teaching_pack.nodes import TeachingPackState
    from services.gateway import teaching_pack_runtime

    # #119 (OPS-06): the graph/quality-gate construction moved out of
    # `main.lifespan` into the shared `teaching_pack_runtime.build_teaching_pack_runtime`
    # builder this session, so both the API process and the standalone
    # worker entrypoint build it identically -- this check follows that move.
    runtime_source = inspect.getsource(teaching_pack_runtime.build_teaching_pack_runtime)
    graph_source = inspect.getsource(build_teaching_pack_graph)
    state_annotations = TeachingPackState.__annotations__
    return {
        "quality_gate_injected": "quality_gate=GatewayTeachingPackQualityGate() if quality_gate_enabled() else None" in runtime_source,
        "middleware_runner_active": (PROJECT_ROOT / "packages" / "llm_client" / "middleware.py").exists(),
        "lead_agent_present": (PROJECT_ROOT / "packages" / "agents" / "lead_agent" / "agent.py").exists(),
        "legacy_graph_present": (PROJECT_ROOT / "packages" / "agents" / "graph.py").exists(),
        "teaching_pack_graph_builder_present": callable(build_teaching_pack_graph),
        "artifact_send_default_enabled": artifact_send_fanout_v1_enabled(),
        "artifact_send_worker_node_present": GENERATE_ONE_ARTIFACT_NODE in graph_source,
        "artifact_send_reducer_channels_present": "artifact_references" in state_annotations and "artifact_workflow_states" in state_annotations,
        "artifact_send_rollback_flag": "OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1",
    }


if __name__ == "__main__":
    write_manifest()
