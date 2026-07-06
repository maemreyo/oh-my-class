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

## Related Documents

- `docs/system/TESTING.md` — concept-level: test layers A/B/C, per-agent contracts
- `docs/system/testing-harness.md` — tiers policy, fixture rules, fake-LLM policy
- `docs/adr/031-full-output-test-matrix.md` — full output test matrix ADR
- `docs/plans/full-system-test-plan-2026-06-25.md` — test plan

---

> Gateway `:8101` · 9router `:20228` model `4omc` · Alembic rev `020_fix_delivery_fk_deferrable`
