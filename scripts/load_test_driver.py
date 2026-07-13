"""Load driver for the QA-02 harness — submits the request plan from
scripts/load_test_profiles.py against a real running gateway at the
scheduled arrival times, concurrently.

Reuses scripts/run_teacher_scenarios.py's RestClient for login/HTTP
plumbing (same auth flow, same error handling) rather than re-implementing
it — this module only adds submission-at-a-schedule and gate-auto-approval
tuned for throughput instead of scenario coverage.

Known gap (stated honestly, not worked around): the gateway's demo auth
(services/gateway/routers/auth_router.py) only has one teacher account
("teacher1") in this environment. Backpressure
(services/gateway/backpressure.py) caps active runs *per teacher* at 3, so
a real run against this demo auth will bottleneck on that single identity
long before 5,000/day concurrency — spreading across many real teacher
identities needs either seeded test accounts or a load-test auth extension,
neither of which exists yet. `--teacher-pool` is wired for when that lands.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent


def _load_scenario_driver_module():
    """Import scripts/run_teacher_scenarios.py by path (it isn't a package),
    same technique tests/test_teacher_scenario_driver.py already uses."""
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    if "run_teacher_scenarios" in sys.modules:
        return sys.modules["run_teacher_scenarios"]
    path = _SCRIPTS_DIR / "run_teacher_scenarios.py"
    spec = importlib.util.spec_from_file_location("run_teacher_scenarios", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_teacher_scenarios"] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True, slots=True)
class SubmissionOutcome:
    run_id: str | None
    mode: str
    submit_offset_seconds: float
    error: str | None


async def _submit_one(
    client: Any,
    mode: str,
    payload: dict,
    offset_seconds: float,
    start_time: float,
) -> SubmissionOutcome:
    now = time.monotonic() - start_time
    delay = offset_seconds - now
    if delay > 0:
        await asyncio.sleep(delay)
    try:
        # RestClient._request is sync (urllib); run it off the event loop so
        # concurrent submissions don't serialize behind one blocking call.
        response = await asyncio.to_thread(client._request, "POST", "/teaching-packs/runs", payload)
        run_id = response.get("run_id")
        if not isinstance(run_id, str):
            return SubmissionOutcome(None, mode, offset_seconds, f"missing run_id in response: {response}")
        return SubmissionOutcome(run_id, mode, offset_seconds, None)
    except Exception as exc:  # noqa: BLE001 - report every failure mode, don't crash the driver
        return SubmissionOutcome(None, mode, offset_seconds, str(exc))


async def _auto_approve_gates(client: Any, run_id: str, deadline: float) -> None:
    """Best-effort: drive any pending gate to 'approve' so runs don't stall
    on a human-in-the-loop step during a load test. Doesn't wait for
    completion — that's the measurement loop's job (load_test_metrics)."""
    while time.monotonic() < deadline:
        try:
            status = await asyncio.to_thread(client.get_status, run_id)
        except Exception:  # noqa: BLE001
            return
        run_status = str(status.get("status", ""))
        if run_status in {"completed", "failed", "cancelled"}:
            return
        raw_gate = status.get("pending_gate")
        if isinstance(raw_gate, dict) and isinstance(raw_gate.get("gate_id"), str):
            action = "answer" if raw_gate.get("gate_name") == "clarification_required" else "approve"
            response_body = {"source": "load_test_driver"}
            if action == "answer":
                response_body["text"] = "Proceed with standard content."
            try:
                await asyncio.to_thread(
                    client._request,
                    "POST",
                    f"/teaching-packs/runs/{run_id}/resume",
                    {
                        "gate_id": raw_gate["gate_id"],
                        "gate_name": raw_gate.get("gate_name"),
                        "action": action,
                        "response": response_body,
                    },
                )
            except Exception:  # noqa: BLE001
                return
        await asyncio.sleep(1.0)


async def run_load_plan(
    *,
    base_url: str,
    plan: list[tuple[float, str, dict]],
    gate_watch_seconds: float = 120.0,
) -> list[SubmissionOutcome]:
    """Submit every (offset, mode, payload) in `plan` at its scheduled offset,
    concurrently, against a real gateway. Returns one SubmissionOutcome per
    planned request (including failures) in submission order."""
    module = _load_scenario_driver_module()
    client = module.RestClient(base_url, timeout_seconds=30.0)
    await asyncio.to_thread(client.login)

    start_time = time.monotonic()
    submit_tasks = [
        asyncio.create_task(_submit_one(client, mode, payload, offset, start_time))
        for offset, mode, payload in plan
    ]
    outcomes = await asyncio.gather(*submit_tasks)

    gate_deadline = time.monotonic() + gate_watch_seconds
    gate_tasks = [
        asyncio.create_task(_auto_approve_gates(client, outcome.run_id, gate_deadline))
        for outcome in outcomes
        if outcome.run_id is not None
    ]
    if gate_tasks:
        await asyncio.gather(*gate_tasks)

    return list(outcomes)
