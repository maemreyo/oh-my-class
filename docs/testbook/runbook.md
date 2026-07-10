# Testing & Artifact Runbook

> **Canonical guide** — how to run the full test suite and produce real HTML artifacts.
> Policy: **real DB + real LLM** (9Router `:20228`, model `4omc`) for eval tiers.
> Deterministic logic is tested without any LLM.

---

## Quick Reference

| What | Command | Notes |
|------|---------|-------|
| Fast suite | `make test` | Python (778 tests) + TypeScript · no LLM · ~30 s |
| Integration only | `make test-integration` | 47 tests · real Postgres · stubbed LLM |
| E2E suite | `uv run pytest tests/e2e/ -v` | 60 tests · stubbed LLM · 4 teacher scenarios |
| Real LLM tests | `uv run pytest tests/e2e/ -v -m real_llm` | Requires 9router :20228 · excluded from CI |
| Headless driver | `uv run python scripts/run_teacher_scenarios.py --base-url http://localhost:8101` | All 4 scenarios → HTML artifacts |
| Fixture mode (offline) | `uv run python scripts/run_teacher_scenarios.py --fixture` | No gateway, no Postgres · <5 s |
| Slide deck release gate | `uv run pytest common/contracts/tests/test_slide_deck_golden_fixtures.py packages/agents/tests/teaching_pack/test_slide_deck_release_gate.py services/gateway/tests/test_teaching_pack_export_writer.py -q && pnpm --dir packages/renderer exec vitest run __tests__/slide-deck-release-gate.test.ts && pnpm --dir apps/web exec playwright test tests/e2e/slide-deck-visual-smoke.spec.ts` | Golden fixtures + pipeline/export + browser visual smoke |

---

## Prerequisites

| Service | Port | Required for | Start command |
|---------|------|-------------|---------------|
| PostgreSQL | 5432 | integration, e2e, driver | `make infra` |
| Gateway | 8101 | driver, manual REST | `make dev-gateway` |
| 9router (LLM proxy) | 20228 | real_llm tests, driver (non-fixture) | external process |
| Node.js | — | renderer (artifact HTML export) | pre-installed |
| Redis | 6379 | optional (caching) | `make infra` |

```bash
# First-time bootstrap
make setup          # uv sync + pnpm install + generate_theme
make infra          # docker compose up db redis
make migrate        # alembic upgrade head

# Start gateway (separate terminal)
make dev-gateway    # uvicorn :8101 with --reload
```

---

## Test Tiers

### Tier 1 · Fast — unit + TypeScript (~30 s, no LLM, no Postgres)

778 Python tests covering storage, control, state machines, quality gates, concurrency,
circuit breakers. Plus renderer, plugin, and component TypeScript tests.

```bash
# Run everything
make test

# Python only
uv run pytest packages/agents packages/quality common/contracts services/gateway tests/ -v

# TypeScript only
pnpm -r test

# Single file
uv run pytest services/gateway/tests/test_teaching_pack_executor.py -v
```

### Tier 2 · Integration — pipeline stage contracts (~60 s, real Postgres, stubbed LLM)

47 tests. Drives data through full pipeline stages (planning → research → content → export)
against a real DB. Validates stage-boundary contracts and render pipeline without calling an
actual LLM.

```bash
# Requires: PostgreSQL running (make infra)
make test-integration

# Equivalent
uv run pytest tests/integration/ -v

# Specific focus areas
uv run pytest tests/integration/test_full_pipeline.py -v
uv run pytest tests/integration/test_component_render_pipeline.py -v
uv run pytest tests/integration/test_stage_seams.py -v
```

### Tier 3 · E2E — teacher scenario workflows (~2 min, real Postgres, stubbed LLM)

60 tests. Runs the 4 canonical teacher scenarios (approve, fast-lane, reject-regenerate,
escalate) and artifact fanout flows against a real DB with deterministic stubbed LLM
responses.

```bash
# All e2e tests
uv run pytest tests/e2e/ -v

# The 4 canonical teacher scenarios
uv run pytest tests/e2e/test_teaching_pack_scenarios.py -v

# Specific scenario
uv run pytest tests/e2e/test_teaching_pack_scenarios.py -v -k "equivalent_fractions"

# Canonical graph execution (detects dark code paths)
uv run pytest tests/e2e/test_canonical_flow.py -v

# Artifact fanout + checkpoint/resume
uv run pytest tests/e2e/ -v -k "artifact_send"
```

### Tier 4 · Real LLM — live inference (~5–15 min, 9router required)

Marked `@pytest.mark.real_llm`. Excluded from per-commit CI. Runs unit flow progression,
failure recovery, and full-flow conformance with actual LLM calls via 9router on
port 20228, model `4omc`.

```bash
# Requires: 9router running on :20228
uv run pytest tests/e2e/ -v -m real_llm

# Override router/model via env
OMC_TEST_9ROUTER_BASE_URL=http://127.0.0.1:20228 \
OMC_TEST_9ROUTER_MODEL=4omc \
  uv run pytest tests/e2e/ -v -m real_llm

# Specific files
uv run pytest tests/e2e/test_unit_flow.py -v -m real_llm
uv run pytest tests/e2e/test_full_flow_conformance.py -v -m real_llm
```

---

## Headless Scenario Driver

`scripts/run_teacher_scenarios.py` drives all 4 teacher scenarios through the full REST API
flow — create → poll → gate-response → resume → export — and writes standalone HTML
artifacts to disk. This is the definitive way to produce real artifacts.

```bash
# Real mode (gateway + Postgres + 9router required)
uv run python scripts/run_teacher_scenarios.py \
  --base-url http://localhost:8101 \
  --output-dir .scratch/teacher-scenarios

# Single scenario: approve | fast_lane | reject_regenerate | escalate
uv run python scripts/run_teacher_scenarios.py \
  --base-url http://localhost:8101 \
  --scenario approve

# Fixture mode — offline, instant, no services needed
uv run python scripts/run_teacher_scenarios.py --fixture
```

### Output locations

| What | Path |
|------|------|
| HTML index | `.scratch/teacher-scenarios/index.html` |
| Summary JSON | `.scratch/teacher-scenarios/summary.json` |
| Per-scenario artifacts | `.scratch/teacher-scenarios/{scenario}/` |
| Gateway raw exports | `.scratch/pipeline-v2/artifacts/exports/{run_id}/` |

### Native slide deck release gate

Use this focused gate after changes to `SlideDeckData`, `SlideDeckEngine`, slide rendering,
teacher preview, scoped regeneration, or export behavior:

```bash
uv run pytest \
  common/contracts/tests/test_slide_deck_golden_fixtures.py \
  packages/agents/tests/teaching_pack/test_slide_deck_release_gate.py \
  services/gateway/tests/test_teaching_pack_export_writer.py -q

pnpm --dir packages/renderer exec vitest run \
  __tests__/slide-deck-renderer.test.ts \
  __tests__/slide-deck-release-gate.test.ts

pnpm --dir apps/web exec playwright test \
  tests/e2e/slide-deck-visual-smoke.spec.ts
```

Covered outputs are recorded as `slide_deck:student`, `slide_deck:teacher`, and
`slide_deck:print`. The gate uses golden fixtures for simple lesson, media-heavy,
interaction, teacher-notes, and answer-leak regression decks. It checks student-facing HTML
for absence of answer keys, correct answers, teacher notes, hidden answer JSON, external
assets in offline mode, and raw provider/debug traces. Browser visual smoke runs at the
configured Playwright widths 375, 768, 1280, and 1920 px and covers slide navigation/reveal
fallback, focus visibility, no horizontal overflow, dark color scheme, and print surface.

---

## Manual REST Walkthrough

Minimal 4-step flow to take a teaching request from nothing to exported HTML artifacts.
Gateway must be running on `:8101`.

### Step 1 — Create a run

```bash
RUN_ID=$(curl -s -X POST http://localhost:8101/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "teacher_id": "teacher-test-001",
    "subject": "Toán",
    "grade_level": "Lớp 5",
    "topic": "Phân số",
    "language": "vi"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['run_id'])")

echo "run_id: $RUN_ID"
```

### Step 2 — Poll until gate opens

```bash
while true; do
  STATUS=$(curl -s http://localhost:8101/runs/$RUN_ID \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])")
  echo "  $STATUS"
  [[ "$STATUS" == "awaiting_approval" || "$STATUS" == "completed" || "$STATUS" == "failed" ]] && break
  sleep 5
done

# Inspect pending gate
curl -s http://localhost:8101/runs/$RUN_ID | python3 -m json.tool
```

Typical wait with real LLM: 60–120 s.

### Step 3 — Respond to the gate

```bash
GATE_ID=$(curl -s http://localhost:8101/runs/$RUN_ID \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['pending_gate']['gate_id'])")

# Approve
curl -s -X POST http://localhost:8101/runs/$RUN_ID/gate-response \
  -H 'Content-Type: application/json' \
  -d "{\"gate_id\": \"$GATE_ID\", \"action\": \"approve\"}"
```

### Step 4 — Poll to completion + verify

```bash
while true; do
  STATUS=$(curl -s http://localhost:8101/runs/$RUN_ID \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])")
  echo "  $STATUS"
  [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]] && break
  sleep 5
done

ls -lh .scratch/pipeline-v2/artifacts/exports/$RUN_ID/
open .scratch/pipeline-v2/artifacts/exports/$RUN_ID/*.html   # macOS
```

---

## Gate Variants

```bash
# Reject a specific artifact and request a revision
curl -s -X POST http://localhost:8101/runs/$RUN_ID/gate-response \
  -H 'Content-Type: application/json' \
  -d "{
    \"gate_id\": \"$GATE_ID\",
    \"action\": \"request_revision\",
    \"artifact_ids\": [\"$ARTIFACT_ID\"],
    \"feedback\": \"Quiz câu hỏi quá khó cho học sinh lớp 5\"
  }"

# Force escalation (test seam — triggers fail_count threshold)
curl -s -X POST http://localhost:8101/runs/$RUN_ID/gate-response \
  -H 'Content-Type: application/json' \
  -d "{\"gate_id\": \"$GATE_ID\", \"action\": \"escalate\"}"

# Cancel at any point
curl -s -X POST http://localhost:8101/runs/$RUN_ID/cancel
```

---

## Verify Artifacts

```bash
# Check DB — recent run statuses
python3 -c "
import psycopg
with psycopg.connect('postgresql://omc_dev:omc_dev@localhost:5432/oh_my_class') as c:
    cur = c.cursor()
    cur.execute(\"SELECT run_id, status FROM public.runs ORDER BY created_at DESC LIMIT 5\")
    for row in cur: print(row[0][:8], row[1])
"

# Verify content (lesson should have headings, quiz should have questions)
python3 -c "
import re, pathlib
run_id = '$RUN_ID'
for f in sorted(pathlib.Path(f'.scratch/pipeline-v2/artifacts/exports/{run_id}').glob('*.html')):
    h = f.read_text()
    qs = re.findall(r'class=\"question-prompt\"[^>]*>(.*?)</p>', h, re.DOTALL)
    print(f.name, f'({len(h)} bytes)', f'{len(qs)} questions' if qs else 'lesson/other')
"

# Re-render all snapshots for a run (use after renderer changes)
python3 -c "
import psycopg, json, subprocess
from pathlib import Path
run_id = '$RUN_ID'
with psycopg.connect('postgresql://omc_dev:omc_dev@localhost:5432/oh_my_class', autocommit=True) as conn:
    cur = conn.cursor()
    cur.execute('SELECT snapshot_id, content_json FROM public.artifact_snapshots WHERE run_id=%s', (run_id,))
    for snap_id, cj in cur.fetchall():
        r = subprocess.run(['node','packages/renderer/dist/agent-renderer.js'],
            input=json.dumps(cj).encode(), capture_output=True, timeout=15)
        html = r.stdout.decode()
        p = Path(f'.scratch/pipeline-v2/artifacts/exports/{run_id}/{snap_id}.html')
        if p.parent.exists(): p.write_text(html)
        cur.execute('UPDATE public.artifact_snapshots SET rendered_html=%s WHERE snapshot_id=%s', (html, snap_id))
        print(snap_id[:20], len(html), 'bytes')
"
```

---

## Canonical Scenarios

Five golden scenarios are the shared input for every test layer. Canonical list lives in `tests/scenarios.py`.

| Key | `raw_request` | Class |
|-----|--------------|-------|
| `math_vn` | "Dạy phân số bằng nhau cho lớp 5. 45 phút." | Grade 5 · math · vi |
| `english_vn` | Present-tense lesson | Grade 6 · english |
| `science_vn` | Photosynthesis | Grade 7 · science |
| `math_basic` | "Teach multiplication tables." | Grade 3 · math |
| `complex_en` | Multi-objective algebra | Grade 8 · math · en |

Each scenario declares expected invariants (not exact output): artifact types produced, ≥2 Bloom levels, standalone HTML, locale match, no answer-key leakage.

---

## pytest Markers

| Marker | Meaning |
|--------|---------|
| `@pytest.mark.real_llm` | Requires 9router on `:20228` · excluded from `make test` |
| `@pytest.mark.e2e` | Full graph execution (60 tests) |
| `@pytest.mark.property` | Adversarial/property-based tests |

Run real_llm tests explicitly: `uv run pytest -m real_llm`. They are **never** run by `make test`.

---

## Slide Deck Production Hardening — Acceptance & Release Evidence (SDH-08)

> Governing decisions: `docs/adr/043-slide-deck-display-preferences-and-projections.md` (display preferences,
> surfaces, print/chrome boundaries) and `docs/adr/044-slide-deck-real-llm-acceptance-harness.md` (real-LLM
> acceptance standard). Full SDH issue set: `gh issue list --search "[SDH-"` (#84–#95 at time of writing).

### Guards vs. acceptance — read this first

Every deterministic/fixture/mock test in this repo (Tiers 1–3 above, the native slide deck release gate,
renderer/vitest/Playwright visual-smoke) is a **technical guard**. Guards catch regressions fast and run in
CI. Per ADR-044, guards are **not acceptance evidence** — a fixture pass can never be reported as proof the
slide-deck feature is done. The only acceptance evidence is a real run of the harness below, against a real
gateway, real Postgres, and a real 9router LLM, with real run/snapshot IDs to show for it.

### Official real-LLM acceptance command

```bash
# Preferred: standalone script (same exit-code contract, forwards pytest's own)
uv run python scripts/slide_deck_acceptance_harness.py

# Equivalent direct invocation
uv run pytest -q services/gateway/tests/test_slide_deck_acceptance_harness.py -k "not test_harness_script"
```

Marked `@pytest.mark.real_llm` — excluded from `make test` and per-commit CI, same tier as the other
real-LLM suites above.

**Required environment (all optional, sane dev-stack defaults shown):**

| Env var | Default | Purpose |
|---|---|---|
| `SDH07_DATABASE_URL` | `postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class` | Async Postgres URL the harness drives the real app/worker against |
| `OMC_9ROUTER_BASE_URL` | `http://127.0.0.1:20228` | Real LLM gateway base URL |
| `OMC_9ROUTER_MODEL` | `4omc` | Model under test; recorded in the evidence bundle's `endpoint_metadata` |
| `SDH07_TEACHER_USERNAME` | `teacher1` | Login identity driven through the real `/auth/login` route (no separate JWT env — the harness logs in for real and never persists the resulting token to disk) |
| `SDH07_RUN_TIMEOUT_SECONDS` | `900` | Max wall-clock time per scenario run before it's classified `infra_fail` |
| `SDH07_EVIDENCE_DIR` | `.scratch/slide-deck-acceptance/artifacts` | Where the evidence bundle and per-scenario exported HTML land |

**Prerequisites:** Postgres reachable and migrated to head (`cd services/gateway && uv run alembic upgrade
head`), a live 9router at `OMC_9ROUTER_BASE_URL` serving `4omc`. If either is unreachable the harness
**skips** (does not silently pass) via its `client` fixture. Browser QA additionally shells out to the real
Playwright install at `apps/web` (`playwright.acceptance.config.ts`); if browsers aren't installed there,
that is recorded honestly as an `infra_fail`-classified `browser_qa` entry, not faked as a pass.

### The three acceptance scenarios

| Scenario | Prompt shape | Locale/subject probe |
|---|---|---|
| `grade5_esl_vocabulary` | Grade 5 ESL food-vocabulary deck with a market-ordering practice activity | English, `food\|fruit\|vegetable\|market\|order` must appear |
| `grade5_math_worked_example` | Grade 5 equivalent-fractions deck, one worked example + independent practice | English, `fraction` must appear |
| `vietnamese_classroom_deck` | Vietnamese-language water-cycle deck with an example and short practice | Vietnamese, `nước\|tuần hoàn\|mưa\|water\|cycle` must appear |

Each scenario is driven end to end through the real gateway HTTP surface (`/teaching-packs/run`, gate
`resume`, snapshot fetch) — not a fixture. **"Passing" means, for a single scenario:**

1. The run reaches `completed` (not `failed`/timed-out) within `SDH07_RUN_TIMEOUT_SECONDS`.
2. A `slide_deck` snapshot is persisted; run ID and snapshot ID are recorded.
3. Deck shape passes: ≥6 slides, required pedagogical spine present (SDH-06's `evaluate_deck_shape`),
   purpose/density check passes, and the scenario's content-probe regex matches somewhere in the deck (proves
   the content is actually about the prompt, not generic filler).
4. Quality/leak-safety passes: `standalone_valid`, no external asset URLs, no answer-key language and no raw
   prompt fragments in `student_rendered_html` (SDH-02's `validate_teacher_only_separation`).
5. Standalone HTML is exported to `SDH07_EVIDENCE_DIR/exports/`, then browser-QA'd for real (Playwright):
   next/prev navigation, no horizontal overflow at 375px, print-media shows all slides, print-mode DOM state
   reflects the selected print settings.
6. A structured-recovery pass (one scenario reused) exercises the real `/request-revision` route and asserts
   the resulting snapshot's content hash actually changed — proving scoped repair, not a blind full retry.

Failures are classified into exactly one of the 7 ADR-044 categories: `generation_sparse`, `quality_fail`,
`leakage`, `export_render_fail`, `browser_nav_fail`, `print_fail`, `infra_fail`.

### Evidence bundle

Written once per full run to `SDH07_EVIDENCE_DIR/sdh-07-evidence.json` (default
`.scratch/slide-deck-acceptance/artifacts/sdh-07-evidence.json`), schema
`oh-my-class.slide_deck_acceptance.evidence.v1`. Contains `endpoint_metadata` (gateway mode, LLM base URL,
model, DB host — never a credential or JWT; the harness itself asserts `"eyJ" not in serialized` before
writing), and one `scenarios[]` entry per scenario with `run_id`, `snapshot_id`, `final_status`,
`gates_driven`, `checks` (the deck-shape/quality/leak booleans above), `export_path`, `browser_qa`, and
`outcome`/`failure_category`/`failure_reason` when failed. Exported student HTML lives alongside it under
`exports/`. As of 2026-07-10 this schema does not yet carry effective display-preferences/projection-surface
lineage or structured-recovery-attempt detail — SDH-10 (open, not yet implemented) extends the schema with
that; treat the fields above as current, not final.

### Release-evidence citation format

A release/implementation report may **not** claim the slide-deck feature done from guard tests alone. For
each of the 3 real scenarios it must cite, inline (not paste the raw bundle):

- run ID
- snapshot ID
- export path
- quality/pass result (deck-shape + leak-safety + browser QA outcome)
- evidence bundle path (`.scratch/slide-deck-acceptance/artifacts/sdh-07-evidence.json` or wherever
  `SDH07_EVIDENCE_DIR` points)

If the harness is unavailable, skipped, or any scenario fails, the report must say so plainly and must not
be represented as release-ready. **Current state:** the evidence bundle on disk as of 2026-07-10 shows all 3
scenarios failing (`quality_fail` on the ESL run's terminal status, `browser_nav_fail`/`infra_fail` on the
other two's browser QA step) — SDH-07 (#90) is deliberately left open pending one more clean run; do not cite
that bundle as a passing release gate until a clean 3-for-3 run replaces it.

### Release checklist

Beyond the real-LLM acceptance run above, a slide-deck release additionally needs:

- [ ] **Student-safe projection** — student/presentation HTML has no teacher notes, answer keys, hidden
      answer JSON, or scrapeable teacher-only fields (SDH-02 `validate_teacher_only_separation`; also
      asserted live by the acceptance harness).
- [ ] **Chrome policy** — no persistent "Generated by oh-my-class" branding on student/presentation surfaces;
      teacher/review surfaces may show provenance (ADR-043 decision 6).
- [ ] **Print layout** — paged grid (`slidesPerPage: 1\|2\|4\|6`) and continuous layouts both show the full
      deck, not just the active slide; print stays independent of on-screen navigation state (ADR-043
      decisions 1, 7).
- [ ] **Border fidelity** — print mode avoids transform scaling, opacity-only borders, filters, shadows, and
      nested rounded-border owners that blur corners (ADR-043 decisions 8–9; SDH-05).
- [ ] **Accessibility** — semantic headings, labeled controls, visible focus, full keyboard navigation, no
      focus traps, `prefers-reduced-motion` respected, no color-only meaning (ADR-043 decision 12).
- [ ] **Real browser QA** — actual exported HTML opened in a real browser: slide navigation, mobile
      readability at 375px (no overflow), print-media rendering — this is the harness's own browser_qa step
      above, not a substitute manual pass.

The existing native slide-deck release gate ("Native slide deck release gate" above) is a fast guard covering
most of this deterministically; treat it as a pre-check, not a replacement for the real-LLM run.

### Scope note: what is *not* v1 (and a correction to ADR-043)

- **Native PDF export is not in v1.** No PDF exporter exists in `ExporterRegistry`
  (`packages/agents/teaching_pack/exporters.py`) or the renderer's export pool. Browser print-to-PDF of the
  `print` surface is the only PDF path, and it is a projection, not a first-class export format.
- **Teacher-notes print is not in v1.** Print projection (ADR-043 decision 7) covers paged/continuous student
  slide layouts only; printing teacher notes/speaker notes onto the physical print surface is explicitly
  listed as future work (ADR-043 decision 7 note, decision 10).
- **Correction:** ADR-043 (written 2026-07-07, still status `Proposed`) lists "native PDF, and PPTX" together
  as deferred future work (decision 7 and the Consequences section). That line is **stale** for PPTX: SDX-05
  (#65, closed 2026-07-09) shipped real `.pptx` export via `ExporterRegistry`
  (`packages/agents/teaching_pack/exporters.py`, `packages/renderer/src/exporters/pptx/index.ts`), verified by
  `packages/renderer/__tests__/exporters/pptx.test.ts` and the architecture-manifest sync test. **PPTX export
  is shipped and in v1; only native PDF export and teacher-notes print remain deferred.** Do not restate
  ADR-043's PPTX line verbatim in future docs — it should be corrected there too, but that edit is out of
  scope for this docs-only slice (ADR text is a historical decision record; this runbook is the place that
  must reflect current shipped reality).

---

## Related Documents

- `docs/system/TESTING.md` — concept-level: test layers A/B/C, per-agent contracts
- `docs/system/testing-harness.md` — tiers policy, fixture rules, fake-LLM policy
- `docs/adr/031-full-output-test-matrix.md` — full output test matrix ADR
- `docs/adr/043-slide-deck-display-preferences-and-projections.md` — display preferences, surfaces, print/chrome ADR
- `docs/adr/044-slide-deck-real-llm-acceptance-harness.md` — real-LLM acceptance standard ADR
- `docs/plans/full-system-test-plan-2026-06-25.md` — test plan

---

> Gateway `:8101` · 9router `:20228` model `4omc` · Alembic rev `020_fix_delivery_fk_deferrable`
