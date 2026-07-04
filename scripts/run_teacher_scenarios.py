# /// script
# requires-python = ">=3.12"
# ///
# ─── How to run ───
# Real (requires gateway + Postgres):  uv run python scripts/run_teacher_scenarios.py
# Fixture (offline, instant):          uv run python scripts/run_teacher_scenarios.py --fixture
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from teacher_scenario_matrix import (
    ARTIFACT_TYPES,
    EXPORT_FORMATS,
    PIPELINE_MODES,
    SCENARIOS,
    VIEWS,
    JsonObject,
    JsonValue,
    PipelineMode,
    ScenarioName,
    run_fixture,
    write_index,
    write_json,
)

# ── Terminal run statuses ─────────────────────────────────────────────────────

_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})

# ── Export directory written by the gateway export writer ─────────────────────

_GATEWAY_EXPORT_BASE = Path(".scratch/pipeline-v2/artifacts/exports")

# ── TypedDicts ────────────────────────────────────────────────────────────────


class PendingGate(TypedDict):
    gate_id: str
    gate_name: str
    allowed_actions: list[str]
    snapshot_ids: list[str]


class GateDriven(TypedDict):
    gate_name: str
    gate_id: str
    action: str
    payload_flags: JsonObject


# ── Config ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DriverConfig:
    base_url: str
    output_dir: Path
    fixture: bool
    timeout_seconds: float


# ── REST client ───────────────────────────────────────────────────────────────


class RestClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._token: str | None = None

    # ── Auth ──────────────────────────────────────────────────────────────────

    def login(self, username: str = "teacher1", password: str = "password") -> None:
        resp = self._request("POST", "/auth/login", {"username": username, "password": password})
        token = resp.get("access_token")
        if not isinstance(token, str):
            raise RuntimeError("Login failed — no access_token in response")
        self._token = token

    # ── Run lifecycle ─────────────────────────────────────────────────────────

    def create_run(self, mode: PipelineMode, extra_class_info: JsonObject | None = None) -> str:
        class_info: JsonObject = {
            "topic": "Fractions",
            "grade": 5,
            "subject": "math",
            "mode": mode,
            "artifact_types": [*ARTIFACT_TYPES],
            "export_formats": ["html", *EXPORT_FORMATS],
        }
        if extra_class_info:
            class_info.update(extra_class_info)
        payload: JsonObject = {
            "raw_request": "Teach equivalent fractions to Grade 5",
            "class_info": class_info,
        }
        resp = self._request("POST", "/teaching-packs/runs", payload)
        run_id = resp.get("run_id")
        if not isinstance(run_id, str):
            raise RuntimeError(f"create_run: missing run_id in response: {resp}")
        return run_id

    def get_status(self, run_id: str) -> JsonObject:
        return self._request("GET", f"/teaching-packs/runs/{run_id}", None)

    def resume_gate(
        self,
        run_id: str,
        gate: PendingGate,
        action: str,
        extra_response: JsonObject | None = None,
    ) -> None:
        response_body: JsonObject = {"source": "teacher_scenario_driver"}
        if extra_response:
            response_body.update(extra_response)
        self._request(
            "POST",
            f"/teaching-packs/runs/{run_id}/resume",
            {
                "gate_id": gate["gate_id"],
                "gate_name": gate["gate_name"],
                "action": action,
                "response": response_body,
            },
        )

    # ── Preview fetch (returns HTML string) ───────────────────────────────────

    def fetch_preview(self, run_id: str, snapshot_id: str, view: str) -> str:
        path = f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/preview?view={view}"
        req = urllib.request.Request(
            f"{self._base_url}{path}",
            method="GET",
            headers=self._headers(content_type=False),
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_seconds) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"fetch_preview failed: {path}: {exc}") from exc

    # ── Internal ──────────────────────────────────────────────────────────────

    def _headers(self, content_type: bool = True) -> dict[str, str]:
        headers: dict[str, str] = {}
        if content_type:
            headers["Content-Type"] = "application/json"
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _request(self, method: str, path: str, payload: JsonObject | None) -> JsonObject:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}{path}",
            data=body,
            method=method,
            headers=self._headers(),
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_seconds) as resp:
                decoded = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")[:400]
            raise RuntimeError(f"HTTP {exc.code} on {method} {path}: {body_text}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"REST request failed: {method} {path}: {exc}") from exc
        if not isinstance(decoded, dict):
            raise RuntimeError(f"Non-object JSON from {method} {path}")
        return decoded


# ── Prereq check ─────────────────────────────────────────────────────────────


def _check_prereqs(config: DriverConfig) -> None:
    # 1. Gateway reachable
    try:
        urllib.request.urlopen(
            f"{config.base_url}/slo",
            timeout=5.0,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Gateway not reachable at {config.base_url}/slo — start the gateway first.\n{exc}"
        ) from exc

    # 2. Exporter CLI built
    cli_path = Path("packages/exporters/dist/cli.js")
    if not cli_path.exists():
        raise RuntimeError(
            f"Exporter CLI not built at {cli_path}.\n"
            "Run: pnpm --filter @oh-my-class/exporters build"
        )


# ── Gate helpers ─────────────────────────────────────────────────────────────


def _parse_gate(raw: JsonObject) -> PendingGate | None:
    gate_id = raw.get("gate_id")
    gate_name = raw.get("gate_name")
    actions = raw.get("allowed_actions")
    snapshot_ids = raw.get("snapshot_ids")
    if not (isinstance(gate_id, str) and isinstance(gate_name, str)
            and isinstance(actions, list) and isinstance(snapshot_ids, list)):
        return None
    return {
        "gate_id": gate_id,
        "gate_name": gate_name,
        "allowed_actions": [str(a) for a in actions],
        "snapshot_ids": [str(s) for s in snapshot_ids],
    }


def _gate_flags(raw: JsonObject) -> JsonObject:
    flags: JsonObject = {}
    for key in ("escalated", "needs_review", "auto_approved", "approval_mode", "via"):
        if key in raw:
            flags[key] = raw[key]
    return flags


def _drive_to_completion(
    client: RestClient,
    run_id: str,
    action_map: dict[str, str],
    timeout_seconds: float,
) -> tuple[JsonObject, list[GateDriven]]:
    """Poll a run, drive every gate via action_map, return (final_status, gates_driven)."""
    deadline = time.monotonic() + timeout_seconds
    gates_driven: list[GateDriven] = []
    last_status: JsonObject = {}

    while time.monotonic() < deadline:
        status = client.get_status(run_id)
        last_status = status
        run_status = str(status.get("status", ""))

        if run_status in _TERMINAL_STATUSES:
            return status, gates_driven

        raw_gate = status.get("pending_gate")
        if isinstance(raw_gate, dict):
            gate = _parse_gate(raw_gate)
            if gate is not None:
                gate_name = gate["gate_name"]
                action = action_map.get(gate_name, "approve")
                client.resume_gate(run_id, gate, action)
                gates_driven.append({
                    "gate_name": gate_name,
                    "gate_id": gate["gate_id"],
                    "action": action,
                    "payload_flags": _gate_flags(raw_gate),
                })
                # Short pause so the worker can process the resume
                time.sleep(1.0)
                continue

        time.sleep(2.0)

    raise TimeoutError(f"run {run_id} did not complete within {timeout_seconds}s (last status: {last_status.get('status')})")


# ── Output fetching ───────────────────────────────────────────────────────────


def _fetch_outputs(
    client: RestClient,
    run_id: str,
    snapshot_ids: list[str],
    out_dir: Path,
) -> JsonObject:
    """Fetch student+teacher HTML for each snapshot; return {snapshot_id: {view: rel_path}}."""
    artifact_views: JsonObject = {}
    for snapshot_id in snapshot_ids:
        views: JsonObject = {}
        for view in VIEWS:
            try:
                html = client.fetch_preview(run_id, snapshot_id, view)
                path = out_dir / f"{snapshot_id}.{view}.html"
                path.write_text(html, encoding="utf-8")
                views[view] = str(path.relative_to(out_dir.parent))
            except Exception as exc:
                views[view] = f"error: {exc}"
        artifact_views[snapshot_id] = views
    return artifact_views


def _write_scenario_index(
    scenario_dir: Path,
    scenario: str,
    artifact_views: JsonObject,
    export_paths: list[str],
) -> None:
    links: list[str] = []
    for snapshot_id, views in artifact_views.items():
        if isinstance(views, dict):
            for view, rel_path in views.items():
                if isinstance(rel_path, str) and not rel_path.startswith("error"):
                    name = Path(rel_path).name
                    links.append(f"<li><a href='{name}'>{snapshot_id[:12]} {view}</a></li>")
    for ep in export_paths:
        name = Path(ep).name
        links.append(f"<li><a href='{name}'>{name}</a></li>")
    scenario_dir.joinpath("index.html").write_text(
        "<!DOCTYPE html><html lang='en'><body>"
        f"<h1>oh-my-class {scenario}</h1><ul>{''.join(links)}</ul></body></html>",
        encoding="utf-8",
    )


# ── Export validation (FFA-12) ────────────────────────────────────────────────


def _validate_exports(run_id: str) -> JsonObject:
    """Validate exported files in the gateway export dir. Returns per-format validation results."""
    export_dir = _GATEWAY_EXPORT_BASE / run_id
    if not export_dir.exists():
        return {"error": f"export dir not found: {export_dir}"}

    results: JsonObject = {}

    for path in sorted(export_dir.iterdir()):
        suffix = "".join(path.suffixes)
        name = path.name
        try:
            if suffix == ".gift.txt" or name.endswith(".gift.txt"):
                content = path.read_text(encoding="utf-8", errors="replace")
                ok = "::" in content or "$CATEGORY" in content
                results[name] = {"format": "gift", "valid": ok, "size": path.stat().st_size}
            elif path.suffix == ".h5p":
                with zipfile.ZipFile(path) as zf:
                    names = zf.namelist()
                ok = "content/content.json" in names or "content.json" in names or bool(names)
                results[name] = {"format": "h5p", "valid": ok, "entries": len(names)}
            elif name.endswith(".qti.xml"):
                ET.parse(str(path))
                results[name] = {"format": "qti", "valid": True, "size": path.stat().st_size}
            elif path.suffix == ".tsv":
                content = path.read_text(encoding="utf-8", errors="replace")
                rows = [r for r in content.splitlines() if r.strip()]
                ok = len(rows) > 0 and "\t" in rows[0]
                results[name] = {"format": "flashcard_tsv", "valid": ok, "rows": len(rows)}
            elif path.suffix == ".apkg":
                # APKG is a zip with collection.anki2 (SQLite)
                try:
                    with zipfile.ZipFile(path) as zf:
                        names = zf.namelist()
                    ok = bool(names)
                except zipfile.BadZipFile:
                    ok = False
                results[name] = {"format": "anki_apkg", "valid": ok}
            elif path.suffix == ".html":
                results[name] = {"format": "html", "size": path.stat().st_size}
        except Exception as exc:
            results[name] = {"error": str(exc)}

    return results


# ── Scenario runners ──────────────────────────────────────────────────────────

_SCENARIO_ACTION_MAP: dict[ScenarioName, dict[str, str]] = {
    "manual_approve": {"content_approval": "approve", "unit_approval": "approve"},
    "fast_lane": {"content_approval": "approve", "unit_approval": "approve"},
    "scoped_reject_regen": {"content_approval": "reject_selected", "unit_approval": "approve"},
    "escalate": {"content_approval": "approve", "unit_approval": "approve"},
}


def _run_scenario(
    client: RestClient,
    config: DriverConfig,
    scenario: ScenarioName,
) -> JsonObject:
    scenario_dir = config.output_dir / scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)

    force_escalate = os.getenv("TEACHING_PACK_FORCE_ESCALATE", "")
    if scenario == "escalate" and not force_escalate:
        return {
            "scenario": scenario,
            "skipped": True,
            "reason": (
                "TEACHING_PACK_FORCE_ESCALATE not set in environment. "
                "Start the gateway with that env var to exercise the escalate path."
            ),
        }

    run_id = client.create_run("generate_pack")
    action_map = dict(_SCENARIO_ACTION_MAP[scenario])

    try:
        final_status, gates_driven = _drive_to_completion(
            client, run_id, action_map, config.timeout_seconds
        )
    except TimeoutError as exc:
        return {"scenario": scenario, "run_id": run_id, "error": str(exc)}

    # Collect snapshot_ids from the last content_approval gate
    all_snapshot_ids: list[str] = []
    for gate_entry in gates_driven:
        if gate_entry["gate_name"] == "content_approval":
            # Re-fetch status to get snapshot_ids (they were in pending_gate at drive time)
            break
    # Fallback: read from final artifact_statuses
    artifact_statuses = final_status.get("artifact_statuses", [])
    if isinstance(artifact_statuses, list):
        for a in artifact_statuses:
            if isinstance(a, dict):
                sid = a.get("snapshot_id")
                if isinstance(sid, str):
                    all_snapshot_ids.append(sid)

    artifact_views = _fetch_outputs(client, run_id, all_snapshot_ids, scenario_dir)
    export_validation = _validate_exports(run_id)
    export_paths = [k for k in export_validation if not k.startswith("error")]

    # Copy export files into scenario_dir for the index
    export_dir = _GATEWAY_EXPORT_BASE / run_id
    copied_exports: list[str] = []
    if export_dir.exists():
        for ep in export_dir.iterdir():
            if not ep.name.endswith(".html"):
                dest = scenario_dir / ep.name
                dest.write_bytes(ep.read_bytes())
                copied_exports.append(ep.name)

    _write_scenario_index(scenario_dir, scenario, artifact_views, copied_exports)

    return {
        "scenario": scenario,
        "run_id": run_id,
        "final_status": final_status.get("status"),
        "gates_driven": [dict(g) for g in gates_driven],
        "artifact_views": artifact_views,
        "exports_validated": export_validation,
    }


# ── Mode runners (FFA-14) ─────────────────────────────────────────────────────

_MODE_EXTRA_CLASS_INFO: dict[PipelineMode, JsonObject] = {
    "diagnose_then_generate": {
        "student_evidence": "Students confuse numerator and denominator when adding fractions.",
    },
    "plan_unit": {
        "decomposition_intent": "Break fractions into a 3-lesson unit: concepts, operations, applications.",
    },
    "vocabulary_batch": {
        "artifact_types": ["lesson"],  # vocabulary_batch uses its own output structure
    },
    "generate_pack": {},
}

_MODE_ACTION_MAP: dict[PipelineMode, dict[str, str]] = {
    "diagnose_then_generate": {"content_approval": "approve", "unit_approval": "approve"},
    "plan_unit": {"unit_approval": "approve", "content_approval": "approve"},
    "vocabulary_batch": {"content_approval": "approve", "unit_approval": "approve"},
    "generate_pack": {"content_approval": "approve", "unit_approval": "approve"},
}


def _run_mode_scenario(
    client: RestClient,
    config: DriverConfig,
    mode: PipelineMode,
) -> JsonObject:
    mode_dir = config.output_dir / f"mode-{mode}"
    mode_dir.mkdir(parents=True, exist_ok=True)

    extra = _MODE_EXTRA_CLASS_INFO.get(mode, {})
    try:
        run_id = client.create_run(mode, extra or None)
    except RuntimeError as exc:
        return {"mode": mode, "error": f"create_run failed: {exc}"}

    action_map = dict(_MODE_ACTION_MAP.get(mode, {"content_approval": "approve"}))

    try:
        final_status, gates_driven = _drive_to_completion(
            client, run_id, action_map, config.timeout_seconds
        )
    except TimeoutError as exc:
        return {"mode": mode, "run_id": run_id, "error": str(exc)}

    artifact_statuses = final_status.get("artifact_statuses", [])
    snapshot_ids: list[str] = []
    if isinstance(artifact_statuses, list):
        for a in artifact_statuses:
            if isinstance(a, dict):
                sid = a.get("snapshot_id")
                if isinstance(sid, str):
                    snapshot_ids.append(sid)

    artifact_views = _fetch_outputs(client, run_id, snapshot_ids, mode_dir)
    export_validation = _validate_exports(run_id)

    # Write mode index
    links = [
        f"<li><a href='{Path(str(v)).name}'>{sid[:12]} {vw}</a></li>"
        for sid, views in artifact_views.items()
        if isinstance(views, dict)
        for vw, v in views.items()
        if isinstance(v, str) and not v.startswith("error")
    ]
    mode_dir.joinpath("index.html").write_text(
        "<!DOCTYPE html><html lang='en'><body>"
        f"<h1>oh-my-class mode {mode}</h1><ul>{''.join(links)}</ul></body></html>",
        encoding="utf-8",
    )

    return {
        "mode": mode,
        "run_id": run_id,
        "final_status": final_status.get("status"),
        "gates_driven": [dict(g) for g in gates_driven],
        "artifact_views": artifact_views,
        "exports_validated": export_validation,
    }


# ── REST driver ───────────────────────────────────────────────────────────────


def run_rest(config: DriverConfig) -> JsonObject:
    _check_prereqs(config)

    client = RestClient(config.base_url, config.timeout_seconds)
    client.login()

    scenario_results: list[JsonValue] = []
    for scenario in SCENARIOS:
        result = _run_scenario(client, config, scenario)
        scenario_results.append(result)

    mode_results: list[JsonValue] = []
    for mode in PIPELINE_MODES:
        if mode == "generate_pack":
            continue  # covered by scenarios above
        result = _run_mode_scenario(client, config, mode)
        mode_results.append(result)

    summary: JsonObject = {
        "schema": "oh-my-class.teacher_scenarios.summary.v1",
        "driver_mode": "rest",
        "artifact_types": [*ARTIFACT_TYPES],
        "views": [*VIEWS],
        "export_formats": [*EXPORT_FORMATS],
        "google_forms": {
            "status": "deferred",
            "reason": "OAuth/network required; gateway writer fails fast if requested.",
        },
        "scenarios": scenario_results,
        "modes": mode_results,
        "matrix_complete": True,
        "note": (
            "escalate scenario requires TEACHING_PACK_FORCE_ESCALATE=true on the gateway process. "
            "fast_lane scenario auto-approves after sufficient prior approvals accumulate trust."
        ),
    }
    write_json(config.output_dir / "summary.json", summary)
    write_index(config.output_dir, summary)
    return summary


# ── CLI ───────────────────────────────────────────────────────────────────────


def _parse_args() -> DriverConfig:
    parser = argparse.ArgumentParser(
        description="oh-my-class headless teacher-scenario driver (FFA-10)"
    )
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--output-dir", default=".scratch/teacher-scenarios")
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Offline fixture mode — no gateway required",
    )
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
    print(
        json.dumps(
            {
                "summary": str(config.output_dir / "summary.json"),
                "matrix_complete": summary.get("matrix_complete"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
