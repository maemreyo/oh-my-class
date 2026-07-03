# [FFA-03] Persist `fail_count` across healing rounds (unfreeze the ladder)

Status: TODO
Labels: full-flow-api, healing
ADR: 029
Depends on: none (foundational for FFA-04/05)

## Context

`fail_count` exists on `TeachingPackState` (`packages/agents/teaching_pack/nodes.py:79`) but
is never incremented/persisted across healing rounds. `HealingOrchestrator.heal` computes
`fail_count = state.get("fail_count",0)+1` (`healing/orchestrator.py`) but the value is not
written back into graph state between quality-failure rounds, so every failure recomputes
`fail_count = 1` → strategy `rewrite`. `reroute`(2)/`replan`(3)/`escalate`(>3) are dead.
This is the root cause behind the orphaned-escalation finding (agents-hardening round 2/3).

## Scope

- [ ] Persist the healing counter into graph state each round so the ladder advances
      retry/rewrite → reroute → replan → escalate. Round-trip through the state reducer,
      not a transient local.
- [ ] Track at the granularity the fan-out supports: per `artifact_id`/`workflow_id` for a
      single failing artifact (aligns with scoped-replan #27), run-level for upstream
      (blueprint/research) failures.
- [ ] Ensure `heal_quality_failure` (`teaching_pack/healing_runtime.py`) reads and writes the
      persisted counter.

## Acceptance

- Unit test: successive quality failures for the same artifact advance
  `fail_count` 1→2→3→>3 and select `rewrite→reroute→replan→escalate` respectively.
- Test: a wave-1 artifact's counter is independent of a wave-2 artifact's (per-artifact).
- No regression in existing healing/orchestrator tests.

## References

- ADR-029. `nodes.py:79` (`fail_count`), `healing/orchestrator.py`,
  `teaching_pack/healing_runtime.py`. Related: agents-hardening #27 (scoped replan).
