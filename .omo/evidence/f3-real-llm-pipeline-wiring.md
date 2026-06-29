# F3: Real Manual QA — Live Pipeline End-to-End Verification

**Date**: 2026-06-30
**Plan**: `real-llm-pipeline-wiring`
**Target Run**: `57561ab4-d813-4ccd-be8d-f402a7f557c7` (COMPLETED, Present Tenses)
**QA Agent**: Sisyphus-Junior

---

## Verdict: REJECT (pre-existing, out of plan scope)

The core pipeline wiring works end-to-end (teacher request → 13 steps → COMPLETED run → stored artifacts → exported HTML). However, **1 out of 4 artifact types (quiz) has a critical student-rendering bug that violates INVARIANT-05 (answer key leakage)**. This blocks student-facing quiz usage.

**Root cause**: `packages/agents/teaching_pack/snapshots.py` `render_student_html()` (line 45) generates minimal HTML but dumps raw JSON section content for quiz artifacts. The `_section_html()` helper (line 70) only handles `heading`/`body`/`content`/`text` fields — quiz questions with `options`/`answer`/`explain` get stringified as raw Python dict text including answer data. This is a **pre-existing bug** in the Python snapshot builder, NOT introduced by this plan's per-artifact generation changes (which modify `packages/agents/sub_agents/content_creator/nodes.py`).

---

## 1. Gateway Health

| Check | Result | Detail |
|-------|--------|--------|
| `GET /health` | **PASS** | HTTP 200, `{"status":"ok","service":"oh-my-class-gateway"}` |
| Response time | **PASS** | 184ms |
| OpenAPI spec | **PASS** | 39 routes registered, all documented |

---

## 2. Run Verification (PostgreSQL)

**Query**: `SELECT run_id, status, raw_request FROM runs WHERE raw_request ILIKE '%present%tense%'`

| Run ID | Status | Created |
|--------|--------|---------|
| `57561ab4-d813-4ccd-be8d-f402a7f557c7` | **COMPLETED** | 2026-06-29 17:50:23 |
| `cf1bf05f-dbf5-48bd-858a-2956c59dbb49` | **COMPLETED** | 2026-06-29 17:09:40 |
| `c193b6ee-4a10-4c28-b977-1356f89ab0ae` | AWAITING_APPROVAL | 2026-06-29 16:10:51 |
| `ac6872bd-32c5-4cf0-a5bd-86c15e717723` | **COMPLETED** | 2026-06-29 15:52:12 |

**DB Stats**: 7 COMPLETED, 13 AWAITING_APPROVAL, 13 FAILED, 55 PENDING, 23 PLANNING

---

## 3. Artifact Snapshot Inspection

**Query**: `SELECT snapshot_id, artifact_type, standalone_valid, approved_at FROM artifact_snapshots WHERE run_id = '57561ab4-...'`

| Snapshot | Artifact | Content | Rendered HTML | Student HTML | standalone_valid | Approved |
|----------|----------|---------|---------------|-------------|------------------|----------|
| `snap-5497cd94edbccd47144889d5` | lesson | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |
| `snap-b30485b1b8485191f66d2b3c` | worksheet | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |
| `snap-c450c5413ad4af80f94a589b` | quiz | **PASS** | **PASS** | **FAIL** | **PASS** | **PASS** |

### Quality Score
- Overall: **8.0 / 10** (PASS threshold: 7.0)
- `all_schema_valid: True`
- `any_exit_ticket: True`
- `lesson_worksheet_quiz_wrong_reasons: True`

### Pedagogy Check
- ✅ Schema valid, exit ticket present
- ✅ Wrong reasons for all distractors
- ✅ Stative verb coverage (know, believe, seem)
- ✅ Transfer items present
- ❌ `homework_model: False` (minor)

---

## 4. Export Verification

**Path**: `.scratch/pipeline-v2/artifacts/exports/57561ab4-d813-4ccd-be8d-f402a7f557c7/`

| File | Size | DOCTYPE | Brand | External URLs | Answer Key Leak | Radio Inputs |
|------|------|---------|-------|---------------|-----------------|--------------|
| `snap-5497cd94edbccd47144889d5.html` (lesson) | 41,430 | **PASS** | **PASS** (3×) | **PASS** (0) | **PASS** (0) | **PASS** (0) |
| `snap-b30485b1b8485191f66d2b3c.html` (worksheet) | 6,122 | **PASS** | **PASS** (3×) | **PASS** (0) | **PASS** (0) | **PASS** (0) |
| `snap-c450c5413ad4af80f94a589b.html` (quiz) | 5,405 | **PASS** | **PASS** (3×) | **PASS** (0) | **PASS** (0) | **FAIL** (1 — native `<input type="radio">`) |

**Invariant Summary**:
- ✅ DOCTYPE present in all 3
- ✅ `oh-my-class` brand string present in all 3 (3 occurrences each)
- ✅ Zero external asset references (CDN-free)
- ✅ Zero answer key references in lesson/quiz exports
- ⚠️ Quiz export has native `<input type="radio">` — but this is the MCQ template, functionally needed
- ⚠️ Quiz export option labels are placeholders ("A", "B", "C", "D" instead of actual answer text — template mapping issue)

---

## 5. Preview Route Verification

**Route**: `GET /teaching-packs/run/{run_id}/snapshots/{snapshot_id}/preview?view=student`
**Auth**: JWT via `POST /auth/login` (teacher1)

### Lesson Preview (student view)
| Check | Result |
|-------|--------|
| HTTP Status | **200** |
| Size | 5,599 bytes |
| Sections | 7 (objectives, trap-first, protocol, film warm-up, guided practice, active recall, exit ticket) |
| DOCTYPE | **PASS** |
| Brand | **PASS** |
| External URLs | **PASS** (0) |
| Answer key leak | **PASS** (0) |
| Content quality | **PASS** — rich inverse-thinking pedagogy, Vietnamese B2 level, proper exit ticket |

### Worksheet Preview (student view)
| Check | Result |
|-------|--------|
| HTTP Status | **200** |
| Size | 5,748 bytes |
| Sections | 6 (instructions, aspect confusion, stative transfer, time-marker mismatch, mixed corpus, exit ticket) |
| DOCTYPE | **PASS** |
| Answer key leak | **PASS** (0 explicit answer key references) |
| Content quality | **PASS** — structured practice sets with progressive difficulty |

### Quiz Preview (student view) — **CRITICAL FAILURE**
| Check | Result |
|-------|--------|
| HTTP Status | 200 |
| Size | 1,636 bytes (vs 5,395 teacher view) |
| Content type | **FAIL** — raw Python dict dump, NOT rendered HTML |
| DOCTYPE | Technically present but body is raw data |
| Answer key leak | **FAIL — CRITICAL** — `teacher_only` section with full answer key (q1-q8 answers) VISIBLE |
| INVARIANT-05 | **VIOLATED** — answer key exposed to student view |

**Quiz student HTML evidence** (verbatim):
```html
<section>teacher_only {&#x27;answer_key&#x27;: [
  {&#x27;question_id&#x27;: &#x27;q1&#x27;, &#x27;answer&#x27;: &#x27;A&#x27;},
  {&#x27;question_id&#x27;: &#x27;q2&#x27;, &#x27;answer&#x27;: &#x27;A&#x27;},
  ...
]}</section>
```

**Root cause**: The quiz artifact's `student_rendered_html` is generated via a fallback path that dumps raw content JSON into minimal HTML wrapper, rather than using the Eta template renderer. The `rendered_html` (teacher view) IS properly rendered with full theme CSS and proper HTML structure. The student rendering path has a regression specific to the quiz artifact type.

### Teacher Preview (lesson view)
| Check | Result |
|-------|--------|
| HTTP Status | **200** |
| Size | 41,430 bytes (full themed HTML) |
| Content | **PASS** — complete lesson with inline SVG icons, themed CSS, print styles |

---

## 6. Browser QA

**Screenshots exist** for run `57561ab4`:
- `lesson-desktop-1280.png`: 1280×900, 304KB, valid PNG ✅
- `lesson-mobile-375.png`: 375×2094, 312KB, valid PNG ✅ (tall = full content rendered)

Note: Could not visually inspect screenshots (model doesn't support image input). File sizes and dimensions indicate non-trivial rendered content.

**Earlier pipeline-v2 browser QA screenshots** (from 2026-06-29):
- `teaching-pack-gate-production-visual-qa.png` — 93KB
- `live-v2-ui-ux-desktop-2026-06-29.png` — 93KB
- `live-v2-ui-ux-mobile-2026-06-29.png` — 91KB
- `live-v2-ui-ux-tablet-2026-06-29.png` — 98KB

---

## 7. Summary

### What Works (Pipeline Wiring)
1. ✅ Gateway serves health + OpenAPI spec
2. ✅ JWT authentication (login → token → authenticated requests)
3. ✅ Run creation via `/teaching-packs/run` API
4. ✅ 13-step pipeline completes (request → COMPLETED status)
5. ✅ Artifacts stored in PostgreSQL with snapshots
6. ✅ Teacher approval gates functional
7. ✅ Lesson content: rich inverse-thinking pedagogy, 7 sections, exit ticket
8. ✅ Worksheet content: 6 practice sections, progressive difficulty
9. ✅ Quality scoring: 8.0/10 (above 7.0 threshold)
10. ✅ Lesson/Worksheet student previews render properly
11. ✅ Lesson teacher preview: full themed HTML (41KB)
12. ✅ Export HTML: standalone, DOCTYPE, brand, no CDN
13. ✅ Preview routes under `/teaching-packs/` prefix work with JWT auth

### What Fails (Template Rendering Regression)
1. ❌ **CRITICAL: Quiz `student_rendered_html` is raw data dump** — 1,636 bytes vs 5,395 teacher view
2. ❌ **CRITICAL: INVARIANT-05 violation** — answer key exposed in quiz student HTML
3. ⚠️ Quiz export HTML option labels are placeholders ("A", "B", "C", "D")
4. ⚠️ `export_paths` empty in probe JSON (no export path tracking)
5. ⚠️ `homework_model: False` in pedagogy check (minor)

### Blocking Issue (out of plan scope)
The quiz student rendering bug is **blocking** because:
- INVARIANT-05 is a hard block: "Answer keys MUST be in teacher_only sections. Student-facing artifacts MUST NOT contain correct answers."
- 1 of 4 artifact types has a broken student preview
- The quiz is unusable in student-facing mode

**However**: This bug is in `packages/agents/teaching_pack/snapshots.py` `render_student_html()`, which is the Python-side snapshot builder. This plan's scope was per-artifact LLM generation (`content_creator/nodes.py`) and component-aware quality gates — neither of which touch the snapshot builder. The `rendered_html` (teacher view) renders correctly via the TypeScript Eta renderer; only the Python `student_rendered_html` fallback path is broken for quiz artifacts.

### Recommendation
Fix `packages/agents/teaching_pack/snapshots.py` `render_student_html()` / `_section_html()` to handle quiz artifacts with `questions` arrays (options, answer, explain) instead of stringifying raw JSON. This is a separate follow-up task outside this plan's scope.
