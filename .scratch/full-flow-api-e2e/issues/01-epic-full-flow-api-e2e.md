# [FFA-01][Epic] Full-flow API operability + teacher-scenario e2e

Status: DONE
Labels: full-flow-api, epic
ADR: 028, 029, 030

## Context

Today a teaching-pack run cannot be driven end-to-end purely over the API, and two
teacher scenarios cannot be produced at all:
- Gate `gate_id`/`snapshot_ids` are only in the SSE stream (no REST discovery) — FFA-02.
- Escalate ("Needs your review") is dead: `fail_count` never persists and the escalate
  route is unwired — FFA-03/04/05.
- `flashcard_deck`/`answer_key`/`roadmap` are not requestable though renderers exist — FFA-06/07/08/09.

This epic tracks making the whole flow API-operable and delivering a headless driver
(FFA-10) that renders the final outputs for all four teacher scenarios (manual approve,
fast-lane auto-approve, scoped reject→regenerate, escalate) across all output types.

## Scope (children)

- [x] FFA-02 REST gate discovery (`pending_gate`)
- [x] FFA-03 Persist `fail_count` across healing rounds
- [x] FFA-04 Wire escalate → `content_approval` (escalated flag)
- [x] FFA-05 `TEACHING_PACK_FORCE_ESCALATE` test seam
- [x] FFA-06 Enable `flashcard_deck`
- [x] FFA-07 Enable `answer_key` + `roadmap`
- [x] FFA-08 Flashcard exports (ADR-024)
- [x] FFA-09 Schema parity for new `ArtifactType`
- [x] FFA-10 Teacher-scenario driver
- [x] FFA-11 Retire legacy `/run` e2e scripts

## Acceptance

- A single command drives create→gate→resume→export purely over REST for all 4 scenarios.
- Final standalone HTML for every requested output type is produced and viewable per scenario.
- Escalate scenario reaches a real teacher gate; fast-lane scenario shows the audited auto-approve gate.
- No use of the decommissioned `/run` (HTTP 410) API anywhere.

## References

- ADR-028/029/030; spec: this folder's sibling issues.
- Companion: `agents-hardening` milestone (state unify, compliance gate, explainable gate #29).
