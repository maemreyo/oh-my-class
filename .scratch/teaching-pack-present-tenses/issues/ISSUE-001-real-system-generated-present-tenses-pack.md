---
title: Generate Present Tenses pack through real Teaching Pack gates
status: completed
labels: [ready-for-agent, teaching-pack, present-tenses, pipeline, gates]
created: 2026-06-29
order: 1
blocked_by: []
---

## What to build

Run the Present Tenses inverse-thinking lesson through the active `/teaching-packs/*` system path so the output is a real system-generated Teaching Pack, not a scratch-authored renderer demo. The completed slice must produce provenance tying the pack to the actual run lifecycle, agent/gate stages, rendered snapshot, approval, and export.

## Acceptance criteria

- [x] A new Present Tenses run is created through the active Teaching Pack API or browser surface with a durable `run_id`.
- [x] Evidence records show the run passed or explicitly opened the relevant teacher gates, including blueprint/content approval semantics where applicable.
- [x] The generated pack includes at least the lesson artifact rendered to standalone HTML through the existing renderer/export path.
- [x] Evidence includes run status, gate/status transitions, rendered snapshot/export path, and whether Planner/Researcher/ContentCreator/Reviewer roles were invoked or bypassed by test configuration.
- [x] The final artifact is not described as system-generated unless provenance evidence exists for that exact `run_id`.
- [x] Real-surface verification opens the generated HTML in a browser and captures screenshot/path evidence.

## Evidence captured

- Active completed run: `ac6872bd-32c5-4cf0-a5bd-86c15e717723`.
- Evidence file: `.scratch/teaching-pack-present-tenses/artifacts/present-tenses-live-completed-run-evidence.json`.
- Gate/event sequence includes `teaching_pack.contract_confirmation.opened`, `teaching_pack.content_approval.opened`, `teaching_pack.content.approved_snapshots`, and `teaching_pack.run.completed`.
- Approved snapshots: `snap-779fa941949414ec6811cb23`, `snap-570b73ea2e3564d33ea4e668`, `snap-bdd09f198501fa6e81153d48`.
- Student preview/export copies are under `.scratch/teaching-pack-present-tenses/artifacts/live-exports/ac6872bd-32c5-4cf0-a5bd-86c15e717723/`.
- Provenance gap recorded honestly: `artifact_ids` is empty and `provider_evidence` is empty for this run, so the evidence proves active lifecycle/snapshot/export provenance but not per-provider LLM/sub-agent attribution.
- System preview behavior was fixed after this run: new snapshots now derive `student_rendered_html` from the renderer output with teacher-only sections removed, instead of lossy JSON fallback text.
- Fresh post-fix completed run: `cf1bf05f-dbf5-48bd-858a-2956c59dbb49`.
- Fresh post-fix evidence file: `.scratch/teaching-pack-present-tenses/artifacts/present-tenses-live-probe.json`.
- Fresh post-fix snapshots: `snap-df36108befb2f3bd178c33a5` (`lesson-1`), `snap-40fa97c7f356893ff64f5491` (`worksheet-2`), `snap-d481d39aae76b35a2c63c76e` (`quiz-3`).
- Fresh post-fix exported lesson: `.scratch/pipeline-v2/artifacts/exports/cf1bf05f-dbf5-48bd-858a-2956c59dbb49/snap-df36108befb2f3bd178c33a5.html`.
- Browser screenshots captured:
  - `.scratch/teaching-pack-present-tenses/artifacts/browser-qa/cf1bf05f-dbf5-48bd-858a-2956c59dbb49/lesson-desktop-1280.png`
  - `.scratch/teaching-pack-present-tenses/artifacts/browser-qa/cf1bf05f-dbf5-48bd-858a-2956c59dbb49/lesson-mobile-375.png`

## Blocked by

None - can start immediately.
