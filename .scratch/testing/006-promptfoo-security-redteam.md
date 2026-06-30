---
title: Promptfoo security & red-team for K-12 safety and invariants
status: ready-for-agent
labels: [ready-for-agent]
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

- [ ] Promptfoo config covers K-12 safety, answer-key leakage, gate bypass, and prompt-injection scenarios.
- [ ] An attempt to leak an answer key into a student section is caught (INVARIANT-05).
- [ ] An attempt to bypass/forge a gate is rejected (INVARIANT-06); legacy `/run/approvals` cannot approve unit gates.
- [ ] Prompt-injection via `raw_request`/sources does not subvert system behavior.
- [ ] Red-team runs are scheduled (periodic + on prompt/model change), routed via 9router; results logged.

## Detailed test suite

(Real LLM via 9router `:20228` / `4omc`.)

- [ ] `tests/security/test_answer_key_leakage.py`: adversarial inputs cannot place answer keys in student-facing sections (gate blocks).
- [ ] `tests/security/test_gate_bypass.py`: resume/approve without a valid gate/owner is rejected; `interrupt()` cannot be skipped.
- [ ] `tests/security/test_prompt_injection.py`: injection payloads in `raw_request`/sources do not exfiltrate or subvert.
- [ ] Promptfoo suite: K-12 safety plugins report zero criticals on the content path (or fail with findings).
- [ ] Run the Promptfoo suite + `uv run pytest -m real_llm tests/security -v`.

## Blocked by

- .scratch/testing/001-harness-and-tiering-foundation.md
