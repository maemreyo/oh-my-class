# [VER-05] Observability live-emitter meta-test
Status: TODO
Labels: verification, ci
ADR: 032
Depends on: none

## Context
ADR-032 Decision 4: "No defined-but-unemitted signals." A meta-test must assert that every
`ObservabilityEventType` in the Literal has a live emitter in production code — this
prevents the round-2/3 recurrence where event types were declared in the enum but never
actually emitted on any runtime path.

The recurrence is present right now and verifiable:

- The event-type Literal is defined at `packages/agents/events.py:23-41`
  (`ObservabilityEventType`), with 18 members including `stage_transition`, `gate_decision`,
  `healing_decision`, `hard_block_violation`, `escalate`, `cost_accrued`, `run_created`,
  `run_failed`, `interrupt`, `step`, `step_started`, `step_completed`, `step_failed`,
  `llm_call_started`, `llm_call_completed`, `llm_call_failed`, `breaker_tripped`.
- Emission goes through `emit_run_event(run_id, event_type, data)` (`events.py:71-73`) and
  `publish_event` (`events.py:76-81`).
- Grepping production code (excluding `events.py` and tests) for each Literal member shows
  **`step_started` and `step_failed` have zero production usages** — they are emitted ONLY
  in `packages/agents/tests/test_events.py` (e.g. lines 32, 49, 76, 154). `step` also has
  no live emitter. These are defined-but-unemitted exactly as ADR-032 warns.
- By contrast, `llm_call_started/completed/failed` and `cost_accrued` are emitted live from
  `packages/agents/llm/chat.py:93,103,143,144`; `escalate`, `stage_transition`,
  `gate_decision`, `healing_decision`, `hard_block_violation`, `breaker_tripped`,
  `run_created`, `run_failed`, `interrupt`, `step_completed` all have production emit sites.

Without a meta-test, a future refactor can drop an emitter (as happened before) and every
existing test stays green because nothing asserts the *type→live-emitter* mapping.

Principle: production-ready, not a patch; live-path proof over coverage-%. The meta-test
proves each declared signal is actually emitted from production code, not merely referenced.

## Scope
- [ ] Add a meta-test (e.g. `tests/guard/test_observability_emitters.py`) that enumerates
  the `ObservabilityEventType` Literal members and asserts each has at least one live
  emitter in production code (an `emit_run_event(..., "<type>", ...)` / `publish_event(...
  event_type="<type>" ...)` call under `packages/`, `services/`, `apps/` — excluding
  `packages/agents/events.py` itself and any `tests/` / `__tests__` path).
- [ ] Read the Literal members programmatically from
  `packages.agents.events.ObservabilityEventType` (via `typing.get_args`) rather than
  hardcoding the list, so adding a new member automatically requires an emitter or the
  meta-test fails.
- [ ] Prefer CodeGraph reachability over a plain grep for the emitter check: resolve the
  emit call sites and confirm each is reachable from a `LIVE_PATH_ROOTS` root (VER-01) —
  i.e. the emitter is not itself dead code. If VER-01's adapter is not yet available, a
  grep-based emitter scan is an acceptable first cut, but note the follow-up to upgrade to
  reachability so a "live emitter" inside an unreachable function does not count.
- [ ] Resolve the current offenders: for `step_started`, `step_failed`, and `step` either
  (a) add real production emitters on the graph/node execution path (e.g. in
  `packages/agents/teaching_pack/nodes.py` node wrappers) so the signals become live, or
  (b) remove the unused members from the Literal. The meta-test must be green either way —
  no defined-but-unemitted members remain.
- [ ] Register the meta-test in the merge gate (it is fast and hermetic).

## Acceptance
- The meta-test fails today against `step_started` / `step_failed` (and `step`) — proving
  it catches the real recurrence — and passes only after each is given a live production
  emitter or removed from the Literal.
- Adding a new member to `ObservabilityEventType` with no production emitter fails the
  meta-test; adding a matching `emit_run_event(..., "<new>", ...)` call on a live path makes
  it pass.
- An emitter that exists only in a test file or in unreachable/dead code does NOT satisfy
  the meta-test (test paths excluded; reachability-checked once VER-01 lands).
- The Literal member list is read via `typing.get_args`, not duplicated in the test.

## References
- ADR-032 (Decision 4: no defined-but-unemitted signals; emitter meta-test)
- `packages/agents/events.py:23-41` (`ObservabilityEventType` Literal), `:71-73`
  (`emit_run_event`), `:76-81` (`publish_event`)
- `packages/agents/llm/chat.py:93,103,143,144` (live emitters: `llm_call_started`,
  `llm_call_failed`, `llm_call_completed`, `cost_accrued`)
- `packages/agents/tests/test_events.py:32,49,76,154` (test-only emissions of
  `step_started`/`step_failed` — do NOT count as live)
- VER-01 live-path adapter (`LIVE_PATH_ROOTS`, reachability) for the "emitter must be
  reachable" upgrade
- `.codegraph/`; `codegraph callers emit_run_event` to enumerate emit sites

## Implementation notes
- Enumerate emit sites robustly: match both `emit_run_event(run_id, "<type>", ...)` (the
  common form) and direct `ObservabilityEvent(..., event_type="<type>")` / `publish_event`
  usages. `codegraph callers emit_run_event` gives the authoritative caller set and lets you
  bind each call's string-literal second argument to a Literal member.
- Exclusion set must cover `packages/agents/events.py` (definition + the store internals),
  `tests/`, `**/tests/`, `**/__tests__/`, and `packages/agents/tests/test_events.py`
  specifically (it exercises every type by design).
- When resolving `step_started`/`step_failed`: the natural live emit point is the per-node
  wrapper in the teaching-pack graph (`make_stage_node` in
  `packages/agents/teaching_pack/nodes.py`, registered at
  `packages/agents/teaching_pack/graph.py:55`) — emitting `step_started` on node entry and
  `step_failed` on node exception mirrors the existing `step_completed` usage and makes the
  signals genuinely live. Prefer adding real emitters over deleting members if the SSE
  stream / observability consumers expect them.
- Verify the live path, not the grep: after adding emitters, drive the compiled graph in a
  test and assert the events actually land in the event store (`get_run_events`) — that is
  the difference between "an emit line exists" and "the signal is emitted at runtime".
