---
title: Prove Present Tenses pack quality gates and invariants
status: completed
labels: [ready-for-agent, teaching-pack, present-tenses, quality-gates]
created: 2026-06-29
order: 2
blocked_by: [ISSUE-001-real-system-generated-present-tenses-pack]
---

## What to build

Attach quality evidence to the real Present Tenses Teaching Pack run. This slice verifies the generated artifacts against the project hard invariants and records any gate failures honestly, without silently replacing system output with hand-authored content.

## Acceptance criteria

- [x] The real generated lesson artifact validates against the canonical artifact contract.
- [x] The rendered HTML contains `<!DOCTYPE html>` and `oh-my-class`.
- [x] The rendered HTML contains no `http://` or `https://` asset references.
- [x] Student-facing HTML does not expose teacher-only answer-key content.
- [x] The quality evidence distinguishes deterministic checks from LLM judge/reviewer checks.
- [x] Any missing Layer 4/Layer 6 judge behavior is recorded as a gap, not claimed as passed.

## Evidence captured

- Deterministic preview checks in `.scratch/teaching-pack-present-tenses/artifacts/present-tenses-live-completed-run-evidence.json` passed for all three approved snapshots:
  - `doctype: true`
  - `brand: true`
  - `no_external_urls: true`
  - `no_answer_markers: true`
- Focused regression coverage added in `services/gateway/tests/test_teaching_pack_previews.py` proves student previews preserve rendered component markup while removing teacher-only answer-key sections.
- Verification commands passed for the preview fix:
  - `uv run pytest services/gateway/tests/test_teaching_pack_previews.py -q` → 8 passed.
  - `uv run ruff check services/gateway/teaching_pack_snapshot_store.py services/gateway/tests/test_teaching_pack_previews.py services/gateway/tests/teaching_pack_preview_fixtures.py services/gateway/tests/teaching_pack_preview_helpers.py services/gateway/tests/teaching_pack_preview_db.py` → all checks passed.
  - `uv run ruff format --check ...` → all checked files formatted.
  - `uv run python -m py_compile ...` → passed.
- Public route probe result for a fresh snapshot: status `200`, rendered `class="lesson-card"` preserved, `Inverse-thinking trap` preserved, `Answer Key` and `Correct answer` removed.
- Quality gap: no Layer 4 or Layer 6 LLM judge evidence exists for completed run `ac6872bd-32c5-4cf0-a5bd-86c15e717723`; this must not be claimed as passed.
- Fresh post-fix run `cf1bf05f-dbf5-48bd-858a-2956c59dbb49` validated the generated gate payload with `common.contracts.artifact.ArtifactContent`:
  - `lesson-1`: `artifact_type=lesson`, `sections=9`.
  - `worksheet-2`: `artifact_type=worksheet`, `sections=6`.
  - `quiz-3`: `artifact_type=quiz`, `sections=8`.
- Fresh post-fix `content_approval` quality payload: `overall: 8.0`, `passed: true`, `snapshot_count: 3`.
- Fresh post-fix exported HTML checks passed for all three exports: `doctype=true`, `brand=true`, `external_urls=false`, `answer_markers=false`, `viewport_meta=true`.
- Fresh post-fix browser console had one non-content error from the temporary localhost static server requesting `/favicon.ico`; no pack script/runtime error was observed.
- Layer 4/Layer 6 judge gap remains: no independent LLM judge records were produced, so this issue is completed for deterministic and contract evidence only.

## Blocked by

- ISSUE-001-real-system-generated-present-tenses-pack
