---
title: Contrastive concept-alignment verifier (KT4EQG)
status: done
labels: []
created: 2026-06-30
---

## What to build

The precondition for trustworthy KT and a real pedagogical metric: verify each generated question actually tests its assigned KC. Per KT4EQG, use sibling KCs (same parent in the prerequisite DAG) as **hard negatives** so the check is interpretable ("Q3 is tagged KC-X but aligns with sibling KC-Y") rather than a vague "off-topic".

- A standalone `concept_alignment` checker (real LLM-judge via 9router) invoked in the reviewer / Layer-4 path: for each question + its `kc_ids`, assess whether answering it **requires** the assigned KC vs a sibling — return an interpretable verdict + suggested correct KC.
- Misalignment feeds **scoped regeneration** (fix the specific question) and, when KC tagging is wrong, corrects `kc_ids`.
- This is one of the **real pedagogical metrics** replacing the stub (issue 002) and **guards KT validity** (mastery per KC is only meaningful if questions truly test their KC).
- Logic is a standalone module injected into the reviewer (reuse 3-vote majority), not a new agent.

## Acceptance criteria

- [x] For each question, the verifier judges KC alignment using sibling-KC hard negatives and returns an interpretable verdict + suggested KC.
- [x] Misaligned questions feed scoped regeneration or `kc_ids` correction through `QualityIssue` + scoped repair parsing.
- [x] The verifier contributes a real `concept_alignment` pedagogical metric (no stub).
- [x] Runs through a 3-vote 9Router/LiteLLM judge seam by default; logic remains standalone/testable via injected transport.
- [x] KT (issue 004) flags low-trust mastery when attempts were not alignment-verified.

## Detailed test suite

(Real LLM via 9router `:20228`/`4omc`.)

- [x] `packages/agents/tests/test_concept_alignment.py`: a question that a sibling KC can answer is flagged misaligned with the suggested KC; a correctly-aligned question passes.
- [x] same file: a misalignment routes to scoped regeneration / `kc_ids` correction.
- [x] same file: injected 3-vote judge seam uses model `4omc` and majority result.
- [x] `packages/agents/tests/test_kt_engine.py`: unverified alignment flags low-trust mastery.
- [x] Run `uv run pytest packages/agents/tests/test_concept_alignment.py packages/agents/tests/test_kt_engine.py -q`.

## Verification

- `uv run pytest packages/agents/tests/test_concept_alignment.py packages/agents/tests/test_kt_engine.py -q` → 8 passed.

## Blocked by

- .scratch/effectiveness-loop/001-outcome-model-and-privacy-foundation.md
