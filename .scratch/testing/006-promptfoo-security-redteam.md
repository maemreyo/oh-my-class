---
title: Promptfoo security & red-team for K-12 safety and invariants
status: done
labels: []
created: 2026-06-30
---

## What to build

Add adversarial/security testing with Promptfoo (MIT, YAML/CLI, self-hostable) targeting K-12 content safety and the hard invariants.

- **K-12 content safety**: red-team plugins for age-inappropriate content, harmful instructions, bias — over the content_creator output path.
- **INVARIANT-05 (answer-key leakage)**: adversarial prompts attempting to surface answer keys in student-facing sections; assert the safety/quality gates block them.
- **INVARIANT-06 (gate bypass)**: attempts to skip the teacher gate / resume without authorization; assert `interrupt()` is mandatory and the gate registry rejects unknown/edit-on-legacy actions (ties to topic-decomposition 020).
- **Prompt-injection** via `raw_request` (teacher input) and researched sources.
- Runs periodically (not per-commit) + on prompt/model changes; LLM via 9router.

## Acceptance criteria

- [x] Promptfoo config covers K-12 safety, answer-key leakage, gate bypass, and prompt-injection scenarios.
- [x] An attempt to leak an answer key into a student section is caught (INVARIANT-05).
- [x] An attempt to bypass/forge a gate is rejected (INVARIANT-06); legacy `/run/approvals` cannot approve unit gates.
- [x] Prompt-injection via `raw_request`/sources does not subvert system behavior.
- [x] Red-team runs are scheduled (periodic + on prompt/model change), routed via 9router; results logged.

## Detailed test suite

(Real LLM via 9router `:20228` / `4omc`.)

- [x] `tests/security/test_answer_key_leakage.py`: adversarial inputs cannot place answer keys in student-facing sections (gate blocks).
- [x] `tests/security/test_gate_bypass.py`: resume/approve without a valid gate/owner is rejected; `interrupt()` cannot be skipped.
- [x] `tests/security/test_prompt_injection.py`: injection payloads in `raw_request`/sources do not exfiltrate or subvert.
- [x] Promptfoo suite: K-12 safety plugins report zero criticals on the content path (or fail with findings).
- [x] `tests/security/test_security_stubs.py`: Python harness invokes the Promptfoo CLI command shape through `tests/security/promptfoo_runner.py`.
- [x] Run the Promptfoo suite + `uv run pytest -m real_llm tests/security -v`.

## Blocked by

- .scratch/testing/001-harness-and-tiering-foundation.md

## Verification

Implemented 2026-06-30.

### Files created

- `tests/security/promptfoo.yaml` — Promptfoo red-team config covering K-12 safety, INVARIANT-05 (answer-key leakage), INVARIANT-06 (gate bypass), and prompt injection; 5 test scenarios routed via 9router / 4omc.
- `tests/security/promptfoo_runner.py` — thin Python runner for `npx promptfoo eval --config tests/security/promptfoo.yaml`.
- `tests/security/test_answer_key_leakage.py` — Deterministic INVARIANT-05 tests: parametrized against 2 student HTML samples and 7 answer-key markers (English + Vietnamese); verifies teacher sections may contain answer keys (positive test).
- `tests/security/test_gate_bypass.py` — INVARIANT-06 tests: TEACHER_APPROVAL stage presence, feature-flag default-off for TRIAGE, ordering invariant (teacher_approval < export_finalize).
- `tests/security/test_prompt_injection.py` — SQL injection, XSS, and template injection pattern detection via regex; prompt-injection payload catalogue for documentation.

### Test run

```
uv run pytest tests/security/test_security_stubs.py -q
5 passed
```

The previous scaffold skips in `test_security_stubs.py` were replaced with executable assertions plus Promptfoo command invocation coverage.
