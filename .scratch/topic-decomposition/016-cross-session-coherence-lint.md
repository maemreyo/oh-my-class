---
title: Cross-session coherence advisory lint
status: done
labels: [done]
completed: 2026-07-01
created: 2026-06-30
---

## What to build

Add the unit-level coherence check (ADR-017 quality tier 3) that catches problems no per-session gate can see. It is **advisory** — it surfaces warnings on the dashboard and never blocks a unit that already passed per-session quality.

Implement as a `coherence_judge` sub-agent (unit-scoped, distinct from the per-artifact `reviewer`) — `packages/agents/sub_agents/coherence_judge/` with logic in `packages/agents/quality/unit_coherence.py`:

- Runs lazily when a unit reaches `complete` (or on demand), over the approved session packs + sequence.
- Checks: terminology consistency across sessions, monotonic difficulty progression, no redundant re-teaching, and that "as learned in session N" references resolve.
- Emits structured `CoherenceWarning[]` (type, involved `session_id`s, message) consumed by the dashboard (`unit.coherence_warning`, issue 011) so the teacher can choose to regenerate a session or dismiss.

## Acceptance criteria

- [x] The coherence pass runs lazily (on `complete` or on demand), never as a blocking gate.
- [x] It produces structured `CoherenceWarning[]` with type + involved sessions + message.
- [x] Warnings surface on the dashboard via the unit event stream; a unit can still be `complete`/exported with open warnings.
- [x] Detects: terminology drift, non-monotonic difficulty, redundant coverage, unresolved back-references.

## Detailed test suite

(Real LLM via 9router port 20228, model `4omc`, for the semantic checks; deterministic for back-reference resolution.)

- [x] `packages/agents/tests/test_unit_coherence.py`: a sequence where session 4 calls a concept "tỉ số" that session 2 called "phân số" yields a terminology warning naming both sessions.
- [x] same file: a sequence whose difficulty dips mid-way yields a monotonic-difficulty warning; a clean sequence yields none.
- [x] same file: an unresolved "as learned in session 9" reference (no such session) yields a back-reference warning (deterministic).
- [x] Non-blocking test: a unit with open coherence warnings is still `complete` and exportable.
- [x] Run `uv run pytest packages/agents/tests/test_unit_coherence.py -v`.

## Blocked by

- .scratch/topic-decomposition/010-unit-orchestrator.md
- .scratch/topic-decomposition/011-unit-read-api-and-streaming.md
