---
title: Loop closure — mastery→planner, MoET sổ theo dõi export, dashboard
status: done
labels: []
created: 2026-06-30
---

## What to build

Close the per-student loop and deliver the "giảm tải sổ sách" payoff.

- **Mastery → planner (channel 1)**: the planner / concept-picker consumes empirical `mastery_for(class, kcs)` as the **third source** alongside declared persona and the taught ClassKnowledgeGraph — low-mastery KCs → reteach/extra practice; high → skip/advance. With low-confidence/cold-start, degrade to persona/KG.
- **MoET sổ theo dõi export (Thông tư 26/2020)**: auto-generate the official tracking sheet from captured outcomes — 0–10 scale, ĐĐGtx/gk/ck columns, required nhận xét, ma trận mapping — as an export artifact (reuse the exporter pattern). This is the primary teacher payoff.
- **Effectiveness dashboard (QĐ764, honest)**: show avg-mastery, %-students-đạt, and trend, framed as the tutor's own improvement view (not external evaluation; no chuẩn-xếp-loại language). **No unverified composite formula / vendor stats** (research flagged 0.4/0.3/0.3, vendor % as unverified — do not ship).

## Acceptance criteria

- [x] The planner/concept-picker uses empirical mastery for assume-vs-reteach; cold-start degrades to persona/KG cleanly.
- [x] A MoET-format sổ theo dõi export is auto-generated (0–10, ĐĐGtx/gk/ck, nhận xét, ma trận) from outcomes.
- [x] An effectiveness dashboard shows avg-mastery / %-đạt / trend transparently, framed as improvement.
- [x] No unverified formula or vendor stat appears in product copy or computation.
- [x] All effectiveness signals are advisory/aggregate (honest attribution).

## Detailed test suite

(Real DB + real LLM via 9router `:20228`/`4omc`.)

- [x] `packages/agents/tests/test_mastery_into_planning.py`: low mastery yields reteach, high mastery assumes, cold-start falls back.
- [x] `packages/agents/tests/test_moet_export.py`: outcomes export to a MoET tracking sheet with period columns/scale/nhận xét/ma trận present and rows derived from attempts.
- [x] `apps/web/tests/effectiveness-dashboard.test.tsx`: dashboard derives avg/%/trend from outcome snapshots; no prohibited evaluation or unverified-number strings present.
- [x] Honesty guard: tests assert no `0.4*...` composite or vendor-stat copy exists in the dashboard output.
- [x] Run `uv run pytest packages/agents/tests/test_moet_export.py -q`: `2 passed`; `pnpm --filter @oh-my-class/web test -- effectiveness-dashboard.test.tsx`: `174 passed`.

## Verification

- `uv run pytest packages/agents/tests/test_moet_export.py -q` → 2 passed.
- `pnpm --filter @oh-my-class/web test -- effectiveness-dashboard.test.tsx` → 174 passed.

## Blocked by

- .scratch/effectiveness-loop/004-bkt-knowledge-tracing-engine.md
