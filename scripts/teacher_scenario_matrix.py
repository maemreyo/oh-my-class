# /// script
# requires-python = ">=3.12"
# ///
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, assert_never

JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]

ArtifactType = Literal[
    "lesson",
    "worksheet",
    "quiz",
    "drill",
    "recap",
    "infographic",
    "flashcard_deck",
    "answer_key",
    "roadmap",
]
ExportFormat = Literal["gift", "h5p", "qti", "flashcard_tsv", "anki_apkg"]
ScenarioName = Literal["manual_approve", "fast_lane", "scoped_reject_regen", "escalate"]
PipelineMode = Literal["generate_pack", "diagnose_then_generate", "plan_unit", "vocabulary_batch"]
ViewName = Literal["student", "teacher"]

ARTIFACT_TYPES: tuple[ArtifactType, ...] = (
    "lesson",
    "worksheet",
    "quiz",
    "drill",
    "recap",
    "infographic",
    "flashcard_deck",
    "answer_key",
    "roadmap",
)
EXPORT_FORMATS: tuple[ExportFormat, ...] = ("gift", "h5p", "qti", "flashcard_tsv", "anki_apkg")
SCENARIOS: tuple[ScenarioName, ...] = (
    "manual_approve",
    "fast_lane",
    "scoped_reject_regen",
    "escalate",
)
PIPELINE_MODES: tuple[PipelineMode, ...] = (
    "generate_pack",
    "diagnose_then_generate",
    "plan_unit",
    "vocabulary_batch",
)
VIEWS: tuple[ViewName, ...] = ("student", "teacher")


def run_fixture(output_dir: Path) -> JsonObject:
    scenario_coverages: list[JsonValue] = [
        _write_fixture_scenario(output_dir, scenario) for scenario in SCENARIOS
    ]
    mode_coverages: list[JsonValue] = [
        _write_fixture_mode(output_dir, mode) for mode in PIPELINE_MODES
    ]
    summary: JsonObject = {
        "schema": "oh-my-class.teacher_scenarios.summary.v1",
        "driver_mode": "fixture",
        "artifact_types": [*ARTIFACT_TYPES],
        "views": [*VIEWS],
        "export_formats": [*EXPORT_FORMATS],
        "google_forms": {
            "status": "deferred",
            "reason": "OAuth/network required and gateway writer fails fast instead of silently skipping.",
        },
        "scenarios": scenario_coverages,
        "modes": mode_coverages,
        "matrix_complete": True,
    }
    write_json(output_dir / "summary.json", summary)
    write_index(output_dir, summary)
    return summary


def write_json(path: Path, data: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_index(output_dir: Path, summary: JsonObject) -> None:
    scenarios = summary.get("scenarios")
    links: list[str] = []
    if isinstance(scenarios, list):
        for scenario in scenarios:
            if isinstance(scenario, dict):
                name = str(scenario.get("scenario", "scenario"))
                links.append(f"<li><a href='{name}/index.html'>{name}</a></li>")
    output_dir.joinpath("index.html").write_text(
        "<!DOCTYPE html><html lang='en'><body><h1>oh-my-class teacher scenarios</h1>"
        f"<ul>{''.join(links)}</ul><a href='summary.json'>summary.json</a></body></html>",
        encoding="utf-8",
    )


def _write_fixture_scenario(output_dir: Path, scenario: ScenarioName) -> JsonObject:
    scenario_dir = output_dir / scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)
    artifact_views: JsonObject = {}
    for artifact_type in ARTIFACT_TYPES:
        views: JsonObject = {}
        for view in VIEWS:
            path = scenario_dir / f"{artifact_type}.{view}.html"
            path.write_text(_html_doc(scenario, artifact_type, view), encoding="utf-8")
            views[view] = str(path.relative_to(output_dir))
        artifact_views[artifact_type] = views
    exports = _write_fixture_exports(scenario_dir, scenario)
    _write_scenario_index(scenario_dir, scenario, artifact_views, exports)
    export_paths: JsonObject = {
        key: str(path.relative_to(output_dir)) for key, path in exports.items()
    }
    return {
        "scenario": scenario,
        "run_id": f"fixture-{scenario}",
        "artifact_views": artifact_views,
        "exports": export_paths,
        "gate_decision": _gate_decision(scenario),
    }


def _write_fixture_exports(scenario_dir: Path, scenario: ScenarioName) -> dict[str, Path]:
    run_id = f"fixture-{scenario}"
    paths = {
        "gift": scenario_dir / f"{run_id}.gift.txt",
        "h5p": scenario_dir / f"{run_id}.h5p",
        "qti": scenario_dir / f"{run_id}.qti.xml",
        "flashcard_tsv": scenario_dir / f"{run_id}.tsv",
        "anki_apkg": scenario_dir / f"{run_id}.apkg",
    }
    paths["gift"].write_text(f"$CATEGORY: oh-my-class/{run_id}\n::q1::Fraction equivalence {{=1/2}}\n", encoding="utf-8")
    paths["h5p"].write_text(json.dumps({"schema": "fixture.h5p", "run_id": run_id}), encoding="utf-8")
    paths["qti"].write_text("<?xml version='1.0'?><assessmentTest identifier='fixture'/>", encoding="utf-8")
    paths["flashcard_tsv"].write_text("front\tback\nEquivalent fraction\tSame value\n", encoding="utf-8")
    paths["anki_apkg"].write_bytes(b"fixture-apkg")
    return paths


def _write_fixture_mode(output_dir: Path, mode: PipelineMode) -> JsonObject:
    mode_dir = output_dir / f"mode-{mode}"
    mode_dir.mkdir(parents=True, exist_ok=True)
    output = mode_dir / "index.html"
    output.write_text(_mode_html(mode), encoding="utf-8")
    return {"mode": mode, "outputs": [str(output.relative_to(output_dir))]}


def _gate_decision(scenario: ScenarioName) -> JsonObject:
    match scenario:
        case "manual_approve":
            return {"decision": "approve", "via": "teacher"}
        case "fast_lane":
            return {"decision": "auto_approved", "via": "fast_lane", "auto_approved": True}
        case "scoped_reject_regen":
            return {"decision": "reject_selected", "via": "teacher", "regenerated": True}
        case "escalate":
            return {"decision": "reject", "via": "teacher", "escalated": True, "needs_review": True}
        case unreachable:
            assert_never(unreachable)


def _html_doc(scenario: ScenarioName, artifact_type: ArtifactType, view: ViewName) -> str:
    return (
        "<!DOCTYPE html><html lang='en'><head><meta name='viewport' content='width=device-width'>"
        f"<title>{scenario} {artifact_type} {view}</title></head>"
        f"<body><main>oh-my-class {scenario} {artifact_type} {view}</main></body></html>"
    )


def _mode_html(mode: PipelineMode) -> str:
    return (
        "<!DOCTYPE html><html lang='en'><head><meta name='viewport' content='width=device-width'>"
        f"<title>{mode}</title></head><body><main>oh-my-class mode {mode}</main></body></html>"
    )


def _write_scenario_index(
    scenario_dir: Path,
    scenario: ScenarioName,
    artifact_views: JsonObject,
    exports: dict[str, Path],
) -> None:
    links = []
    for artifact_type, views in artifact_views.items():
        if isinstance(views, dict):
            for view, relative_path in views.items():
                links.append(f"<li><a href='{Path(str(relative_path)).name}'>{artifact_type} {view}</a></li>")
    for export_format, path in exports.items():
        links.append(f"<li><a href='{path.name}'>{export_format}</a></li>")
    scenario_dir.joinpath("index.html").write_text(
        "<!DOCTYPE html><html lang='en'><body>"
        f"<h1>oh-my-class {scenario}</h1><ul>{''.join(links)}</ul></body></html>",
        encoding="utf-8",
    )
