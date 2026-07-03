# [FFA-10] Headless teacher-scenario driver (`scripts/run_teacher_scenarios.py`)

Status: TODO
Labels: full-flow-api, e2e, testing
ADR: 028, 029, 030, 031
Depends on: FFA-02, FFA-04, FFA-05, FFA-06, FFA-07, FFA-08, FFA-12, FFA-14

## Context

There is no working headless driver for the current `/teaching-packs/*` API (the legacy
scripts use the decommissioned `/run` 410 API — see FFA-11). We need one command that runs
each teacher scenario and writes the final standalone HTML so outputs are inspectable.

## Scope

- [ ] `scripts/run_teacher_scenarios.py` (httpx) driving pure REST:
      login (`POST /auth/login`, teacher1) → create (`POST /teaching-packs/runs`) →
      poll `GET /runs/{id}` for `pending_gate` (FFA-02) → resume → poll → fetch outputs.
- [ ] Scenarios:
      1. manual approve (approve content gate) → export
      2. fast-lane auto-approve (approve one run to build trust, set `GATE_FAST_LANE_THRESHOLD`
         > 0, re-run same teacher → auto_approved gate visible)
      3. scoped reject → regenerate one artifact (`reject_selected` / request-revision)
      4. escalate (`TEACHING_PACK_FORCE_ESCALATE`) → "Needs your review" gate
- [ ] Cover the FULL output matrix (ADR-031): request ALL 9 artifact types (lesson, worksheet,
      quiz, drill, recap, infographic, flashcard_deck, answer_key, roadmap) with BOTH student and
      teacher HTML views, and export_formats `[html, gift, h5p, qti, flashcard_tsv, anki_apkg]`
      (assessment exports via FFA-12; google_forms deferred per FFA-13). Cover each pipeline mode
      (FFA-14). Record matrix coverage in summary.json (no silent gaps).
- [ ] Output per scenario to `.scratch/teacher-scenarios/<NN-scenario>/`:
      per-artifact `preview` HTML (student + teacher view), copied exported files, and an
      `index.html` linking everything; plus a top-level `index.html` + `summary.json`
      (gate events, decision/via, trust_score, healing_history, revision_count, timings).
- [ ] Modes: real-LLM (default, per real-not-mock policy, 9router :20228 / model 4omc) and an
      optional fixture-LLM mode for fast CI.
- [ ] Prereqs auto-check: Postgres up, gateway up (worker in-process), exporter CLI built;
      clear error if missing. Do NOT restart the gateway mid-run (in-memory checkpointer).

## Acceptance

- `python scripts/run_teacher_scenarios.py` produces `.scratch/teacher-scenarios/index.html`
  linking all 4 scenarios, each showing every output type's final HTML (student/teacher).
- `summary.json` records gate decisions incl. auto_approved/via=fast_lane and escalated.
- Runs purely over REST (no SSE dependency), no `/run` (410) calls.

## References

- ADR-028/029/030. Integration spec (auth, create, gate sequence, resume, preview, exports).
  `services/gateway/routers/teaching_pack_runs.py`, `teaching_pack_previews.py`,
  `teaching_pack_export_writer.py` (`.scratch/pipeline-v2/artifacts/exports/<run_id>/`).
