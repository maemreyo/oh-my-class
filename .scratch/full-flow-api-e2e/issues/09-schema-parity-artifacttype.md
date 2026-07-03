# [FFA-09] Schema parity for new `ArtifactType` members (Pydantic ↔ Zod)

Status: DONE
Labels: full-flow-api, contracts, schemas
ADR: 030
Depends on: none (do before FFA-06/07)

## Context

Adding `answer_key`/`roadmap` (and admitting `flashcard_deck`) changes the `ArtifactType`
Literal in `common/contracts/run_contract.py`. This is a cross-language contract: Pydantic
(Python) + generated Zod/TS (`common/schemas/src/generated/*`). Drift here breaks the web
client and the parity check (`make check-schemas`).

## Scope

- [x] Update `ArtifactType` Literal in `common/contracts/run_contract.py` (add answer_key,
      roadmap; flashcard_deck already present).
- [x] Regenerate Zod/TS schemas (`make gen-schemas`) and verify parity (`make check-schemas`).
- [x] Update any `ArtifactContent.artifact_type` Literal (`common/contracts/artifact.py`) if
      it diverges; confirm renderer contract types match.
- [x] Update `SUPPORTED_ARTIFACTS`-style validation set(s) consistently.

## Acceptance

- `make check-schemas` passes (Pydantic ↔ Zod parity).
- Web typecheck passes with the new members.
- One source of truth: no hand-maintained duplicate type list drifts.

## References

- ADR-030. `common/contracts/run_contract.py:11`, `common/contracts/artifact.py`,
  `common/schemas/src/generated/*`, `scripts/generate_zod_schemas.py`, `make gen-schemas/check-schemas`.
