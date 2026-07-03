# /// script
# requires-python = ">=3.12"
# ///
# ─── How to run ───
# uv run python scripts/run_teacher_scenarios.py --fixture
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from teacher_scenario_matrix import (
    ARTIFACT_TYPES,
    EXPORT_FORMATS,
    SCENARIOS,
    JsonObject,
    JsonValue,
    PipelineMode,
    ScenarioName,
    run_fixture,
    write_index,
    write_json,
)


class PendingGate(TypedDict):
    gate_id: str
    gate_name: str
    allowed_actions: list[str]
    snapshot_ids: list[str]


@dataclass(frozen=True, slots=True)
class DriverConfig:
    base_url: str
    output_dir: Path
    fixture: bool
    timeout_seconds: float


class RestClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def create_run(self, scenario: ScenarioName, mode: PipelineMode = "generate_pack") -> str:
        payload: JsonObject = {
            "raw_request": f"Teach fractions for {scenario}",
            "class_info": {
                "topic": "Fractions",
                "grade": 5,
                "subject": "math",
                "mode": mode,
                "artifact_types": [*ARTIFACT_TYPES],
                "export_formats": ["html", *EXPORT_FORMATS],
            },
        }
        response = self._request("POST", "/teaching-packs/runs", payload)
        run_id = response.get("run_id")
        if not isinstance(run_id, str):
            raise RuntimeError("create run response missing run_id")
        return run_id

    def wait_for_pending_gate(self, run_id: str) -> PendingGate:
        deadline = time.monotonic() + self._timeout_seconds
        while time.monotonic() < deadline:
            response = self._request("GET", f"/teaching-packs/runs/{run_id}", None)
            gate = response.get("pending_gate")
            if isinstance(gate, dict):
                gate_id = gate.get("gate_id")
                gate_name = gate.get("gate_name")
                actions = gate.get("allowed_actions")
                snapshot_ids = gate.get("snapshot_ids")
                if isinstance(gate_id, str) and isinstance(gate_name, str) and isinstance(actions, list) and isinstance(snapshot_ids, list):
                    return {
                        "gate_id": gate_id,
                        "gate_name": gate_name,
                        "allowed_actions": [str(action) for action in actions],
                        "snapshot_ids": [str(snapshot_id) for snapshot_id in snapshot_ids],
                    }
            time.sleep(1.0)
        raise TimeoutError(f"run {run_id} did not expose pending_gate")

    def resume_gate(self, run_id: str, gate: PendingGate, action: str) -> None:
        self._request(
            "POST",
            f"/teaching-packs/runs/{run_id}/resume",
            {
                "gate_id": gate["gate_id"],
                "gate_name": gate["gate_name"],
                "action": action,
                "response": {"source": "teacher_scenario_driver"},
            },
        )

    def _request(self, method: str, path: str, payload: JsonObject | None) -> JsonObject:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"REST request failed: {method} {path}: {exc}") from exc
        if not isinstance(decoded, dict):
            raise RuntimeError(f"REST request returned non-object JSON: {method} {path}")
        return decoded


def run_rest(config: DriverConfig) -> JsonObject:
    client = RestClient(config.base_url, config.timeout_seconds)
    scenario_results: list[JsonValue] = []
    for scenario in SCENARIOS:
        run_id = client.create_run(scenario)
        gate = client.wait_for_pending_gate(run_id)
        action = "reject_selected" if scenario == "scoped_reject_regen" else "approve"
        client.resume_gate(run_id, gate, action)
        scenario_results.append({
            "scenario": scenario,
            "run_id": run_id,
            "gate": {
                "gate_id": gate["gate_id"],
                "gate_name": gate["gate_name"],
                "allowed_actions": [*gate["allowed_actions"]],
                "snapshot_ids": [*gate["snapshot_ids"]],
            },
            "action": action,
        })
    summary: JsonObject = {
        "schema": "oh-my-class.teacher_scenarios.summary.v1",
        "driver_mode": "rest",
        "scenarios": scenario_results,
        "matrix_complete": False,
        "note": "REST mode drove create → pending_gate discovery → resume. Fetch/copy outputs after gateway completion.",
    }
    write_json(config.output_dir / "summary.json", summary)
    write_index(config.output_dir, summary)
    return summary


def _parse_args() -> DriverConfig:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--output-dir", default=".scratch/teacher-scenarios")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    args = parser.parse_args()
    return DriverConfig(
        base_url=str(args.base_url),
        output_dir=Path(str(args.output_dir)),
        fixture=bool(args.fixture),
        timeout_seconds=float(args.timeout_seconds),
    )


def main() -> None:
    config = _parse_args()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    summary = run_fixture(config.output_dir) if config.fixture else run_rest(config)
    print(json.dumps({"summary": str(config.output_dir / "summary.json"), "matrix_complete": summary.get("matrix_complete")}, indent=2))


if __name__ == "__main__":
    main()
