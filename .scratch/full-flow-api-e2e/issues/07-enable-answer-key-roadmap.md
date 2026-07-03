# [FFA-07] Enable `answer_key` + `roadmap` end-to-end (INVARIANT-05)

Status: TODO
Labels: full-flow-api, contracts, content, safety
ADR: 030
Depends on: FFA-09 (schema parity)

## Context

Renderer plugins exist for `answer_key` (`packages/renderer/src/plugins/answer-key.ts`) and
`roadmap` (`.../roadmap.ts`) with contracts + sanitizer configs, but neither is in the
`ArtifactType` Literal (`common/contracts/run_contract.py:11`) nor the requestable set, so
they cannot be requested. `answer_key` is safety-sensitive: answer keys must remain
teacher-only and never leak into student HTML (INVARIANT-05; enforced by the compliance gate).

## Scope

- [ ] Add `answer_key` and `roadmap` to the `ArtifactType` Literal + supported/validation set.
- [ ] `content_creator` generation contracts (prompt + RCM + richness) for both.
- [ ] Fan-out dependencies: `answer_key` depends on the assessment artifacts it keys
      (quiz/worksheet/drill); `roadmap` depends on `lesson`.
- [ ] `answer_key` content is emitted into `teacher_only` sections only.
- [ ] Extend INVARIANT-05 tests: student view of an `answer_key`-bearing pack contains NO
      answer markers; teacher view does. Run through the real compliance gate.

## Acceptance

- Both types requestable and rendered (student/teacher views correct).
- INVARIANT-05 behavioral test passes for `answer_key` (no student leakage; compliance gate
  blocks a leaked answer key).
- Fan-out + scoped-replan handle both.

## References

- ADR-030, INVARIANT-05, ADR-026 (compliance gate). renderer `plugins/{answer-key,roadmap}.ts`,
  `run_contract.py:11`, compliance policy (`packages/quality/compliance_policy.py`).
