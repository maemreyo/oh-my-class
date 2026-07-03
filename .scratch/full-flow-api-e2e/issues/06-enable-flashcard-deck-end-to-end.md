# [FFA-06] Enable `flashcard_deck` end-to-end

Status: TODO
Labels: full-flow-api, contracts, content
ADR: 030
Depends on: FFA-09 (schema parity)

## Context

`flashcard_deck` is already in the `ArtifactType` Literal (`common/contracts/run_contract.py:11`)
and has a renderer plugin (`packages/renderer/src/plugins/flashcard-deck.ts` + contract +
sanitizer config), but it is NOT in the requestable/supported artifact set used at contract
setup, so requesting it trips the `clarification_required` gate. Rendering is not the gap —
contract admission + content generation + export wiring are.

## Scope

- [ ] Add `flashcard_deck` to the supported/validation artifact set (the set that currently
      admits only lesson/worksheet/quiz/drill/recap/infographic).
- [ ] Add `content_creator` prompt-contract + `ARTIFACT_RICHNESS` + RCM component contract for
      `flashcard_deck` so it generates `ArtifactContent` the renderer plugin accepts.
- [ ] Slot `flashcard_deck` into the artifact fan-out dependency graph (depends on `lesson`);
      ensure scoped-replan (#27) reasons about it.
- [ ] Contract/round-trip test for the generated `flashcard_deck` artifact.

## Acceptance

- A create request with `artifact_types` including `flashcard_deck` starts cleanly (no
  clarification gate) and produces a rendered `flashcard_deck` snapshot (student view).
- Fan-out + scoped-replan handle it correctly.

## References

- ADR-030. `run_contract.py:11`, renderer `plugins/flashcard-deck.ts`,
  content_creator prompt_contract / ARTIFACT_RICHNESS, artifact fan-out.
