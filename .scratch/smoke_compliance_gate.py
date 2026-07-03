"""Smoke driver: independently verify compliance-gate module surface.

Exercises:
  1. route_after_render_quality (no issues → compliance_gate)
  2. compliance_gate with valid state → passes → teacher_approval
  3. compliance_gate with missing doctype → fails → artifact_workflow
  4. compliance_gate with external CDN → fails → artifact_workflow
  5. compliance_gate with PII in artifact content → fails
  6. compliance_gate with answer key in student HTML → fails
  7. ObservabilityEvent 'hard_block_violation' emitted on failure
  8. Teacher-only answer key allowed (no violation)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.agents.teaching_pack.compliance import compliance_gate_state, evaluate_compliance
from packages.agents.teaching_pack.nodes import TeachingPackState, route_after_compliance_gate
from packages.agents.teaching_pack.quality_routing import route_after_render_quality
from packages.agents.events import clear_run, get_run_events


def _student_html(body: str) -> str:
    return (
        "<!DOCTYPE html><html lang='en'>"
        "<head><meta name='viewport' content='width=device-width'></head>"
        f"<body>oh-my-class {body}</body></html>"
    )


def _teacher_html(body: str) -> str:
    return (
        "<!DOCTYPE html><html lang='en'>"
        "<head><meta name='viewport' content='width=device-width'></head>"
        f"<body>oh-my-class {body}</body></html>"
    )


def _valid_artifact() -> dict:
    return {
        "artifact_id": "quiz-1",
        "artifact_type": "quiz",
        "theme": "default",
        "title": "Fractions Quiz",
        "sections": [{"title": "Q1", "content": "What is 1/2 + 1/4?"}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }


def _valid_snapshot(student_html: str | None = None, teacher_html: str | None = None) -> dict:
    return {
        "snapshot_id": "snap-1",
        "student_rendered_html": student_html or _student_html("What is 1/2 + 1/4?"),
        "rendered_html": teacher_html or _teacher_html("Teacher notes."),
    }


def _full_state(**overrides) -> dict:
    base = {
        "run_id": "smoke-run",
        "artifacts": [_valid_artifact()],
        "rendered_snapshots": [_valid_snapshot()],
    }
    base.update(overrides)
    return base


PASS = "PASS"
FAIL = "FAIL"
results: list[tuple[str, str, str]] = []  # (test_name, verdict, detail)


def check(name: str, condition: bool, detail: str = "") -> None:
    verdict = PASS if condition else FAIL
    results.append((name, verdict, detail))
    sym = "✓" if condition else "✗"
    print(f"  {sym} {name}: {verdict}" + (f" — {detail}" if detail else ""))


# ── Test 1: render_quality success routes to compliance_gate ─────────────
print("\n[T1] route_after_render_quality (no issues → compliance_gate)")
route = route_after_render_quality({"run_id": "smoke"})
check("T1a: route == 'compliance_gate'", route == "compliance_gate", f"got '{route}'")


# ── Test 2: Valid state passes compliance gate ───────────────────────────
print("\n[T2] Valid compliance state passes → teacher_approval")
result = compliance_gate_state(_full_state())
check("T2a: compliance_passed is True", result["compliance_passed"] is True)
route = route_after_compliance_gate(result)
check("T2b: routes to teacher_approval", route == "teacher_approval", f"got '{route}'")


# ── Test 3: Missing doctype fails ────────────────────────────────────────
print("\n[T3] Missing doctype → fails → artifact_workflow")
bad_html = "<html lang='en'><body>oh-my-class content</body></html>"
state = _full_state(rendered_snapshots=[_valid_snapshot(student_html=bad_html)])
result = compliance_gate_state(state)
check("T3a: compliance_passed is False", result["compliance_passed"] is False)
check("T3b: violation contains 'missing_doctype'", "missing_doctype" in result["compliance_result"]["violations"],
      str(result["compliance_result"]["violations"]))
route = route_after_compliance_gate(result)
check("T3c: routes to artifact_workflow", route == "artifact_workflow", f"got '{route}'")
check("T3d: fail_layer == 'compliance'", result.get("fail_layer") == "compliance")
check("T3e: fail_type == 'hard_block'", result.get("fail_type") == "hard_block")


# ── Test 4: External CDN asset fails ─────────────────────────────────────
print("\n[T4] External CDN link → fails")
cdn_html = _student_html("<link href='https://cdn.example.test/tailwind.css'>")
state = _full_state(rendered_snapshots=[_valid_snapshot(student_html=cdn_html)])
result = compliance_gate_state(state)
check("T4a: compliance_passed is False", result["compliance_passed"] is False)
check("T4b: violation contains 'external_assets'", "external_assets" in result["compliance_result"]["violations"],
      str(result["compliance_result"]["violations"]))


# ── Test 5: PII in artifact content fails ────────────────────────────────
print("\n[T5] PII (email) in artifact content → fails")
pii_artifact = {
    "artifact_id": "ws-1",
    "artifact_type": "worksheet",
    "theme": "default",
    "title": "Contact Worksheet",
    "sections": [{"title": "Info", "content": "Email jane@example.test for homework help."}],
    "metadata": {},
    "accessibility": {"language": "en"},
}
state = _full_state(artifacts=[pii_artifact])
result = compliance_gate_state(state)
check("T5a: compliance_passed is False", result["compliance_passed"] is False)
check("T5b: violation contains 'pii_leakage'", "pii_leakage" in result["compliance_result"]["violations"],
      str(result["compliance_result"]["violations"]))


# ── Test 6: Answer key in student HTML fails ─────────────────────────────
print("\n[T6] Answer key in student HTML → fails")
answer_html = _student_html("The answer is A. Answer key: A=3, B=5")
state = _full_state(rendered_snapshots=[_valid_snapshot(student_html=answer_html)])
result = compliance_gate_state(state)
check("T6a: compliance_passed is False", result["compliance_passed"] is False)
check("T6b: violation contains 'answer_key_leakage'", "answer_key_leakage" in result["compliance_result"]["violations"],
      str(result["compliance_result"]["violations"]))


# ── Test 7: ObservabilityEvent emitted ───────────────────────────────────
print("\n[T7] ObservabilityEvent 'hard_block_violation' emitted on failure")
run_id = "smoke-observe"
clear_run(run_id)
state = _full_state(run_id=run_id, rendered_snapshots=[_valid_snapshot(student_html=bad_html)])
result = compliance_gate_state(state)
events = get_run_events(run_id)
hard_block_events = [e for e in events if e["event_type"] == "hard_block_violation"]
check("T7a: at least 1 hard_block_violation event", len(hard_block_events) >= 1,
      f"got {len(hard_block_events)} events")
if hard_block_events:
    evt = hard_block_events[0]
    check("T7b: event has run_id", evt["run_id"] == run_id)
    check("T7c: event has 'code' (top-level from payload)", "code" in evt)
    check("T7d: event code is 'missing_doctype'", evt.get("code") == "missing_doctype", f"got {evt.get('code')}")
    check("T7e: event has 'reason' (top-level from payload)", "reason" in evt)
    check("T7f: event has 'location' (top-level from payload)", "location" in evt)
    check("T7g: event_type is 'hard_block_violation'", evt["event_type"] == "hard_block_violation")


# ── Test 8: Teacher-only answer key allowed ──────────────────────────────
print("\n[T8] Answer key only in teacher HTML → allowed (no violation)")
teacher_answer_html = _teacher_html("Answer: A=3, B=5. Full rubric here.")
state = _full_state(rendered_snapshots=[_valid_snapshot(teacher_html=teacher_answer_html)])
result = compliance_gate_state(state)
check("T8a: compliance_passed is True", result["compliance_passed"] is True)


# ── Test 9: No events emitted on pass ────────────────────────────────────
print("\n[T9] No hard_block_violation events when compliance passes")
run_id_pass = "smoke-pass"
clear_run(run_id_pass)
state = _full_state(run_id=run_id_pass)
result = compliance_gate_state(state)
events_pass = get_run_events(run_id_pass)
check("T9a: compliance_passed is True", result["compliance_passed"] is True)
check("T9b: no hard_block_violation events", len(events_pass) == 0,
      f"got {len(events_pass)} events")


# ── Summary ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
failed = [r for r in results if r[1] == FAIL]
total = len(results)
passed_count = total - len(failed)
print(f"Results: {passed_count}/{total} passed, {len(failed)} failed")
if failed:
    print("\nFAILURES:")
    for name, verdict, detail in failed:
        print(f"  ✗ {name}: {detail}")
    print("\nOVERALL: FAIL")
    sys.exit(1)
else:
    print("\nOVERALL: PASS")
    sys.exit(0)
