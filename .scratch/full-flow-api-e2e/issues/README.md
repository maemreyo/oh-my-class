# full-flow-api-e2e — issue set

Goal: make the entire teaching-pack flow operable via API and provide a headless
teacher-scenario driver that renders the final outputs for every scenario.
Local tracking only (not created on GitHub remote).

Guiding principle (per project standing): production-ready rebuilds over patches;
big-bang physical change + guard tests; high-readability, SoC, modular, testable.

ADRs: `docs/adr/028-full-rest-operability-teaching-pack-runs.md`,
`docs/adr/029-healing-escalation-to-teacher-review.md`,
`docs/adr/030-full-artifact-type-and-export-coverage.md`,
`docs/adr/031-full-output-test-matrix.md`.

| # | Title | ADR |
|---|-------|-----|
| FFA-01 | [Epic] Full-flow API operability + teacher-scenario e2e | 028/029/030/031 |
| FFA-02 | REST gate discovery — `pending_gate` on GET /runs/{id} | 028 |
| FFA-03 | Persist `fail_count` across healing rounds (unfreeze ladder) | 029 |
| FFA-04 | Wire escalate route → `content_approval` with `escalated` flag | 029 |
| FFA-05 | `TEACHING_PACK_FORCE_ESCALATE` test seam + guard | 029 |
| FFA-06 | Enable `flashcard_deck` end-to-end | 030 |
| FFA-07 | Enable `answer_key` + `roadmap` end-to-end (INVARIANT-05) | 030 |
| FFA-08 | Implement ADR-024 flashcard exports (`flashcard_tsv`/`anki_apkg`) | 030/024 |
| FFA-09 | Schema parity for new `ArtifactType` members (Pydantic↔Zod) | 030 |
| FFA-10 | Headless teacher-scenario driver (`scripts/run_teacher_scenarios.py`) | 028/029/030/031 |
| FFA-11 | Retire stale legacy `/run` e2e scripts | — |
| FFA-12 | Assessment export coverage — gift / h5p / qti | 031/030 |
| FFA-13 | google_forms export — decide scope + dry-run | 031 |
| FFA-14 | Pipeline-mode coverage — diagnose / plan_unit / vocabulary_batch | 031 |

## Full output matrix (ADR-031) — what the FULL test must cover

- **HTML** × 9 artifact types × {student, teacher} view: lesson, worksheet, quiz, drill, recap,
  infographic, flashcard_deck, answer_key, roadmap.
- **Assessment exports** (wired): gift, h5p, qti (from quiz/worksheet/drill).
- **Flashcard exports** (wired, CLI): flashcard_tsv, anki_apkg (from flashcard_deck).
- **google_forms**: deferred (OAuth/network, unwired in gateway) → FFA-13.
- **Modes**: generate_pack, diagnose_then_generate, plan_unit (unit_approval + roadmap), vocabulary_batch.
- **Teacher scenarios**: manual approve · fast-lane · scoped reject→regen · escalate.

Dependency order: FFA-09→FFA-06→FFA-07→FFA-08; FFA-02; FFA-03→FFA-04→FFA-05;
FFA-12, FFA-13, FFA-14 → FFA-10 (driver) → FFA-11 (cleanup).
