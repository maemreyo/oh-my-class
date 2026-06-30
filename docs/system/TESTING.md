# Testing the system — canonical guide

> How to test oh-my-class end-to-end and per-part. Policy: **real DB + real LLM** (9Router `:20228`, model `4omc`) — no fake-LLM. Deterministic logic is tested without the LLM.

The mental model: **teacher sends a prompt → [system works] → teacher gets output.** Tests must (1) drive that whole flow automatically for a few scenarios, and (2) test each phase/agent in isolation, then compose them.

---

## 0. One source of truth: scenarios

A few golden scenarios are the shared input for **every** test layer (per-agent, per-stage, full-flow). Canonical list lives in `tests/scenarios.py` (promoted from `scripts/test_e2e_real_llm.py`):

| key | prompt (raw_request) | class_info |
|---|---|---|
| `math_vn` | "Dạy phân số bằng nhau cho lớp 5. 45 phút." | grade 5, math, vi |
| `english_vn` | present-tense lesson, grade 6 | grade 6, english |
| `science_vn` | photosynthesis, grade 7 | grade 7, science |
| `math_basic` | "Teach multiplication tables." | grade 3, math |
| `complex_en` | multi-objective algebra, grade 8 | grade 8, math, en |

Each scenario also declares **expected invariants** (not exact output): artifact types produced, ≥2 Bloom levels, standalone HTML, locale match, no answer-key leakage.

---

## 1. Three test layers (build up, then compose)

```
Layer A — per-agent      (real LLM)      planner · researcher · content_creator · reviewer
Layer B — per-stage      (real graph)    each of the 8 stages, fed the prior stage's output (seam tests)
Layer C — full-flow      (real graph)    scenario prompt → whole pipeline → output + architecture conformance
```

### Layer A — per-agent (real LLM)
For each sub-agent, run it on the relevant scenario slice and assert its **output contract + behavior**:
- `planner_node` → valid `LessonPlan`, ≥2 Bloom levels, locale match.
- `researcher_node` → `ResearchBundle` with sources.
- `content_creator_node` → `ArtifactContent[]` matching requested types, no placeholder/answer-key leakage.
- `reviewer_node` → quality scores in range.
Run: `uv run pytest -m real_llm packages/agents/tests/ -k "node and scenario"`.

### Layer B — per-stage (real graph, one stage at a time)
Invoke each stage node with the previous stage's output and assert the **seam contract** (producer output ⊆ consumer input): `setup_contract → preplanning_search → planning_blueprint → post_blueprint_research → artifact_workflow → render_quality → teacher_approval → export_finalize`. Catches integration breaks without running the whole pipeline.
Run: `uv run pytest tests/integration/test_stage_seams.py -v`.

### Layer C — full-flow (the "prompt → output" test)
For each scenario, drive the **real** `build_teaching_pack_graph().ainvoke()` (or the live gateway) from prompt to exported output, auto-approving gates, and assert **architecture conformance**:
- stages traversed in order (`completed_stages` == the 8-stage sequence, mode-aware);
- gates fired in order: `contract_confirmation → (search_plan_confirmation) → blueprint_approval → content_approval`;
- artifacts produced for requested types; quality ran; export produced (HTML today);
- terminal status `completed`; teacher-visible output retrievable.

This is the layer that proves the system "works according to the architecture."

---

## 2. Run the full flow — one command

```bash
make e2e            # infra check + migrate + 9Router(:20228) check + gateway(:8001) + run all scenarios
make e2e SCEN=math_vn
```

`make e2e` (to be standardized — see `testing/008`) does:
1. ensure `db`+`redis` up (`make infra`) and migrated (`make migrate`);
2. assert 9Router reachable on `:20228` (real LLM);
3. start the gateway on the e2e port, wait for `/health`;
4. run the scenario driver (`scripts/test_e2e_real_llm.py`) → for each scenario: login → create run → poll SSE → approve each gate → poll → verify invariants;
5. print a teacher-style summary (artifacts + timings) and write outputs to `.scratch/api-test-output/`.

> **Port note (fix in `technical-debt/005`):** the e2e tooling targets `:8001`; the dashboard/`make dev` use `:8101`. `make e2e` must pin one port consistently.

### Manual full flow (see it in the UI)
```bash
make dev            # infra + gateway + web
# login teacher1 → /runs/new → submit prompt → approve gates live via SSE → view exported HTML
```

### Direct graph (debug, no gateway/queue)
```bash
uv run python scripts/test_full_flow.py    # build_teaching_pack_graph().ainvoke()
```

---

## 3. Deterministic vs real-LLM tiers

- **Per-commit (fast, no LLM):** store-level lifecycle + status/gate transitions (`tests/e2e/test_teaching_pack_deterministic.py`), stage trajectory/seam contracts, validators. `uv run pytest -m "not real_llm"`.
- **Nightly / pre-release (real LLM):** Layer A/C scenarios, golden-dataset regression. `uv run pytest -m real_llm`.

> Today `tests/e2e/conftest.py` mocks the LLM at the store level — that's the deterministic tier. The real-LLM full flow is `scripts/test_e2e_real_llm.py`. Keep both; don't conflate.

---

## 4. Prerequisites checklist

- [ ] `db` + `redis` up (`make infra`), migrations applied (`make migrate`).
- [ ] 9Router running on `:20228` (operator's local), model `4omc` reachable.
- [ ] Gateway on the e2e port (`:8001` for the driver) — or use `make e2e`.
- [ ] For UI: `make dev`, login `teacher1`.

---

## 5. What the tests will (honestly) show today (as-built)

- Quality at `render_quality` is **thin** (schema+regex+coherence) — the 6-layer gate is not injected yet; export is **HTML only**. Full-flow tests assert against this as-built reality (and will tighten as `runtime-parity/001` + `/005` land).
- The deterministic e2e tests drive orchestration at the **store level**, not the real graph — Layer C (real-graph conformance) closes that gap (`testing/008`).

---

*See `.scratch/testing/` (harness epic) and `testing/008` (canonical flow harness) for the implementation issues.*
