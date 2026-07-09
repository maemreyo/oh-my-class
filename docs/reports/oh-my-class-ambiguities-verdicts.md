# oh-my-class — Verdicts on System Ambiguities

> Derived from the 12 system-trace documents (`00-index.md` → `12-skills.md`,
> `system-diagram.md`) and the architecture diagram built from them. Every
> "Verdict" reflects what the **traced source code** actually does — not what
> `AGENTS.md` claims. Severity legend:
> 🔴 Critical (breaks builds / security / prod behavior) · 🟠 High (real behavior
> materially differs from documented behavior) · 🟡 Medium (dead/unwired code,
> no user-facing effect yet) · ⚪ Low (naming/cosmetic only).
>
> **Resolution legend** (added 2026-07-09 after grill session):
> ✅ Resolved — grill decision confirmed, fix direction decided
> 🔧 In progress — implementation underway or planned
> 📋 Work item — requires separate implementation effort
> 🗑️ Delete — code/file planned for removal

## Executive summary

The repo has **three recurring patterns** behind almost every ambiguity below:

1. **Docs describe an earlier or aspirational design** (fewer stages, single
   gate, multi-judge consensus, LiteLLM-fronted proxy) that code has since
   diverged from, usually *expanding* scope without updating `AGENTS.md`.
2. **Registered ≠ wired.** Several subsystems (quality-tier middleware, TS
   exporters, top-level skill files, multi-judge Layer 4/6) exist fully in
   source but have **no runtime call site** — they read as "done" in a repo
   search but do nothing at request time.
3. **Two schema/config sources coexist** where one is supposed to be
   canonical (theme tokens, LLM proxy topology, gate registries), and nothing
   enforces which one wins.

None of these are contradictions in the *code* — the code is internally
consistent. The ambiguity is entirely **docs-vs-code**, which is the
dangerous kind: an engineer reading `AGENTS.md` will build the wrong mental
model and ship changes against a topology that doesn't exist.

---

## 01 — Teaching-Pack Stage Graph

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 1.1 | Stage count: AGENTS.md says "9 stages" (heading) and "8-stage StateGraph" (body) | Neither is right. Code has **10** stages by default, **12** with `FEATURE_COMPONENT_STRATEGIST_V1` on. | 🟠 High | ✅ K1: Update AGENTS.md to reflect 10-stage default + 12-stage component-strategist variant. |
| 1.2 | Default sequence order | Real order inserts `triage` right after `setup_contract`, not documented. The feature-flagged 12-stage variant also **reorders** `teacher_approval` before `artifact_workflow` — a structurally different pipeline, not just a longer one. | 🟠 High | ✅ K1: Document `triage` as live default stage; document component-strategist reordering. |
| 1.3 | HITL gate count | Docs imply one `teacher_approval` gate. Code has **two** `interrupt()` gates (`unit_approval`, `teacher_approval`) on different pipeline paths (`plan_unit` vs `generate_pack` mode). `unit_approval` never reaches export. | 🟠 High | ✅ K1: Document both gates and their pipeline paths. |
| 1.4 | Conditional seams: "3 conditional seams" | Actual graph wires **6** conditional edges (triage, unit_approval, artifact fan-out, render_quality 5-way, compliance_gate, teacher_approval). | 🟡 Medium | ✅ K1: Update from "3" to "6" conditional edges. |

**Verdict:** The graph is a superset of what's documented, plus one whole
alternate mode (`plan_unit`) that AGENTS.md doesn't model at all. Anyone
debugging routing off AGENTS.md's mental map will miss the `triage` branch
and the unit-planning gate entirely.

**Grill resolution (§01):** ✅ K1 + L2.
- AGENTS.md updates to reflect runtime: 10-stage default, 12-stage variant, 6 conditional seams, both HITL gates.
- Add hard rule in AGENTS.md: every change to `graph.py`, `stages.py`, routing functions, or feature-flag stage variants must update AGENTS.md/docs in the same PR.
- Add L2 test-enforced graph contract (`docs/runtime/teaching-pack-graph-contract.json`) compared by a snapshot test against runtime stage tuples and conditional routes. CI fails if contract drifts from code.

---

## 02 — Sub-Agents

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 2.1 | Agent count: docs list 6 | **9** agent directories exist; `unit_planner`, `practice_generator`, `coherence_judge` are undocumented. | 🟠 High | ✅ M1: Update agent list in AGENTS.md to match actual directories. |
| 2.2 | Model names: `deepseek-v4-flash`, `deepseek-free`, `gpt-5.4` | No such strings in source. Every agent defaults to `"4omc"`, overridable per-task via `MODEL_<TASK>` env vars. | 🟠 High | ✅ M1: Remove stale DeepSeek/GPT model tables. Source of truth = `packages/agents/config/models.py`. Default = `"4omc"`. Overrides: `MODEL_STRONG_DEFAULT`, `MODEL_FAST_DEFAULT`, `MODEL_<TASK>`. |
| 2.3 | `max_turns` 80/120 | Not a real config. Only `max_retries=3` exists; token ceilings are per-agent via `MaxTokensConfig`, unrelated to "turns." | 🟡 Medium | ✅ M1: Remove `max_turns` claims from AGENTS.md. Document actual config (`max_retries`, `MaxTokensConfig`). |
| 2.4 | Reviewer = "direct LLM judge call" | Reviewer never calls an LLM directly — it constructs `AdaptiveJudge` and delegates transport back through the same `AgentRuntime`, adding multi-judge dispatch + deterministic hard-block override on top. | 🟠 High | ✅ M1: Update AGENTS.md reviewer description to reflect AdaptiveJudge + multi-judge dispatch. |
| 2.5 | Roadmap agent has its own model field | It reuses the strong-tier `MODELS.blueprint_design` alias; there is no `MODELS.roadmap_agent`. | 🟡 Medium | ✅ M1: Update roadmap agent description to reference `MODELS.blueprint_design`. |

**Verdict:** The "6 agents, deepseek/gpt models, turn-budgeted" description
is stale on every axis. Treat `packages/agents/config/models.py` as the only
source of truth for model names — anything in prose docs about model choice
should be assumed wrong until re-verified.

**Grill resolution (§02):** ✅ M1.
- Remove all DeepSeek/GPT model name tables from AGENTS.md §6.
- Add single source-of-truth statement: `packages/agents/config/models.py` owns model assignments.
- Document env override pattern: `MODEL_STRONG_DEFAULT`, `MODEL_FAST_DEFAULT`, `MODEL_<TASK>`.
- Add sync rule: model assignment changes require docs update.

---

## 03 — Middleware Stack

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 3.1 | "23 layers, ~200 lines each, one `BaseMiddleware` interface" | 23-layer/order/interface claim is **correct**. The "~200 lines each" claim is **false** — most files are 27–55 lines; only one file (`sequence_consistency_validator.py`, 206 lines) is actually that size. | ⚪ Low | ✅ Docs fix: correct "~200 lines each" to actual sizes. |
| 3.2 | Implied: all 23 middlewares run per request | Only **~10** run (`RUN_ENTRY`, `GENERATION_CONTEXT`, `GATE_LAYER` groups). The 6-entry `QUALITY_GATE_CONSOLIDATED` group (curriculum, readability, pedagogical, bias, artifact coherence, LO alignment) is registered but **has no caller** in `middleware_runtime.py`. | 🔴 Critical | 🔧 A2 + B1: Wire `QUALITY_GATE_CONSOLIDATED_MIDDLEWARE` into `render_quality` via helper; warning-only first (not hard-block). |

**Verdict:** This is the most consequential silent gap in the whole system.
Quality-related middleware (bias detection, readability, curriculum
alignment, pedagogical quality) *looks* fully implemented in a code search
but **never executes**. Anyone relying on AGENTS.md's implication that these
run will over-trust output quality. This should be flagged to product/eng
as a real gap, not just a doc fix.

**Grill resolution (§03):** 🔧 A2 + B1.
- Add runtime hook for `QUALITY_GATE_CONSOLIDATED_MIDDLEWARE` in `render_quality` stage, invoked via helper (e.g. `run_quality_consolidated_middleware(state, context)`).
- Phase 1: warning-only. Middleware results written as quality signals/metadata into state, NOT blocking pipeline.
- Downstream (`render_quality` routing or reviewer) may use signals to trigger rewrite/recovery.
- Do NOT hard-block on these middlewares in phase 1 — risk of breaking pipeline with unwired dead code.
- Update AGENTS.md: clarify that quality middlewares run in `render_quality` as advisory signals, not hard gates.

---

## 04 — Agent Cross-Cutting Infra

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 4.1 | `gates.py`, `healing.py`, `observability.py` described as single files | Each is a **package** (`gates/`, `healing/`, `observability/`) with sub-modules (`fact_check/`, `presentation/`, `strategies/`). Naming-only mismatch, but it changes where a change actually needs to land. | ⚪ Low | ✅ Docs fix: update file descriptions to match actual package structure. |
| 4.2 | Layer 4 "3 independent judge calls → majority vote" | `GateConfig.judge_n = 1` — explicitly commented "K4: 1 judge MVP, bump to 3 later." Single heuristic judge, not 3. | 🟠 High | ✅ N2: Change `GateConfig.judge_n` default to `3`. Make 3-judge behavior explicit, not accidental. |
| 4.3 | Layer 6 "3 independent judges (2/3 pass)" | Not implemented at all. `export_consensus_threshold` is dead config, only meaningful once `judge_n==3`. | 🟠 High | 📋 O2: Wire `export_consensus_threshold` into Layer 6 as required work item. NOT delete — keep config, add implementation requirement. |
| 4.4 | `age_checker.GRADE_LEVEL_COMPLEX_THRESHOLD` | Defined but **never read** by `check_age_appropriateness` — only the `BLOCKED_FOR_K12` regex is enforced. Grade-complexity limits are dead config. | 🟡 Medium | 📋 Work item: wire or remove `GRADE_LEVEL_COMPLEX_THRESHOLD`. |

**Verdict:** The system currently ships an intentionally-reduced Layer 4/6
(single judge, MVP) that reads in docs like a mature 3-judge consensus
system. This is a scoped-down MVP decision, correctly commented in source —
but it means quality scores are less robust than AGENTS.md implies, and
should be communicated as a known limitation, not hidden behind stale docs.

**Grill resolution (§04):** ✅ N2 + 📋 O2.
- `GateConfig.judge_n` changed from `1` to `3`. Remove "MVP" comment.
- Production reviewer wiring made explicit: `AdaptiveJudge(num_judges=gate_config.judge_n)`.
- `export_consensus_threshold` kept (NOT deleted) — becomes required implementation work item for Layer 6 export readiness consensus.
- Tests updated for 3-judge default; unit tests may override `num_judges=1` for speed.

---

## 05 — Quality Gates

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 5.1 | `Score = Layer1×0.15 + Layer2×0.55 + Layer3×0.30` | This notation conflates two different things. The 15/55/30 weights are **Layer 4's own rubric criteria** (format/content/presentation), not a weighted sum across the six *sequential* pipeline layers. There is no cross-layer weighted score anywhere in source. | 🟠 High | ✅ S1: Rewrite AGENTS.md. Sequential pass/fail gates. 15/55/30 = Layer 4 internal rubric only. No weighted cross-layer score. |
| 5.2 | Pedagogical metrics: "7 binary metrics" | Source defines **10**: 5 measured now, 5 explicitly deferred to a post-delivery loop. The "7" number doesn't correspond to anything in code. | 🟡 Medium | ✅ S1: Update to "10 metrics (5 active, 5 deferred)". |
| 5.3 | Layer 3 responsive check: Playwright at 375/768/1280/1920px | `check_responsive` short-circuits to `passed=True` whenever `environment=="development"`; the Playwright block is a commented TODO. It **always passes** in dev regardless of viewport. | 🟠 High | 📋 T3: Honest docs + required work item for Playwright responsive validation. |

**Verdict:** The scoring formula in AGENTS.md is not just imprecise, it
describes a mechanism (weighted multi-layer score) that doesn't exist — the
real gate is sequential pass/fail per layer with Layer 4 alone using
internal weights. Anyone tuning "quality thresholds" against the documented
formula would be editing the wrong knob.

**Grill resolution (§05):** ✅ S1 + 📋 T3.
- Remove misleading weighted formula from AGENTS.md.
- Document as: 6 sequential gates, critical/hard-block fail stops pipeline, Layer 4 uses 15/55/30 rubric internally.
- Do NOT create new cross-layer weighted aggregate score.
- Responsive check: update AGENTS.md to say dev short-circuits / lightweight check only. Staging/prod target: real Playwright viewport validation. Add as required work item (not implemented in first wave).

---

## 06 — Renderer

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 6.1 | Sanitizer = DOMPurify | Real sanitizer is `sanitize-html`. `dompurify` is a listed but **unused, dead** package dependency. | 🟡 Medium | 🗑️ Delete `dompurify` from package.json. |
| 6.2 | "6 page templates" | Real `templates/pages/` has **13** (6 named + `teaching_pack`, `slide_deck`, `reading_passage`, `exit_ticket`, `answer_key`, `roadmap`, `flashcard_deck`). | 🟡 Medium | ✅ Docs fix: update template count. |
| 6.3 | Theme source of truth | **Two parallel, unsynced schemas** coexist: legacy flat `common/branding/kits/*/theme.json` and the active 3-tier `ThemeTokens` in `packages/renderer/src/theme/themes/*.json`. The renderer loads only the latter at runtime. | 🟠 High | ✅ I1 + J3: Renderer `ThemeTokens` = canonical. Migrate accessibility/typography/labels from common branding, then DELETE `common/branding/kits`. |
| 6.4 | Implied `inlineCss()` utility | Doesn't exist — CSS is inlined natively in `templates/base.html` via `<%~ it.themeCSS %>`. | ⚪ Low | ✅ Docs fix: remove `inlineCss()` reference. |

**Verdict:** #6.3 is the one worth acting on. `common/branding` theme edits
have **no effect on rendered output** unless someone also updates
`packages/renderer/src/theme/themes/*.json` by hand — there is no sync step.
This is a live foot-gun for whoever owns branding/theming.

**Grill resolution (§06):** ✅ I1 + J3.
- Renderer `ThemeTokens` (3-tier: primitives/semantic/component) is the single canonical source.
- `common/branding/kits/*/theme.json` is NOT canonical.
- Migrate from common branding to renderer themes:
  - Accessibility metadata (`accessibility` block from `high-contrast-dyslexia` → optional `accessibility?` field in `ThemeTokens`)
  - Typography extras (`line-height`, `letter-spacing` → optional `lineHeightScale`/`letterSpacing` in primitives)
  - Vietnamese category labels (`groups` → optional `categoryLabels` in semantic/metadata)
- After migration: DELETE `common/branding/kits/` entirely.
- Update AGENTS.md invariant: canonical = renderer `ThemeTokens`, NOT common branding.

---

## 07 — Exporters

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 7.1 | "All formats generated from the same `ArtifactContent` JSON" | False for the path that actually runs. The gateway's active exporter (`FileSystemTeachingPackExportWriter`) writes **simplified Python skeletons** for gift/h5p/qti (e.g. an empty `{}` body, a bare `<assessmentItem>` stub) — it does not call the real TS exporters at all. | 🔴 Critical | 📋 C1: Bridge gateway to TS CLI for GIFT/H5P first; replace Python skeletons with real TS exporters via subprocess path (same pattern as Anki/TSV). |
| 7.2 | Unified `generateGift`/`generateH5P`/`generateQTI` entrypoints | All three **throw `Not yet implemented`**. They are stubs, full stop. | 🔴 Critical | 📋 C3: Fix public TS entrypoints after C1. Not blocking first wave. |
| 7.3 | QTI multi-file ZIP (imsmanifest + assessments/test + items) | Does not exist anywhere in source. Only a flat skeleton and an unrelated inverse-thinking QTI path exist. | 🟠 High | 🗑️ D1: Replace QTI skeleton with explicit unsupported/error. No fake XML output. Full QTI implementation = separate workstream. |
| 7.4 | GIFT type coverage | Real TS `gift-impl` covers all listed question types **except `numerical`**. | 🟡 Medium | ✅ Docs: document GIFT coverage accurately. |
| 7.5 | H5P Blanks mapper | Implemented (`clozeToH5PBlanks`) but **never imported or called** by `H5PExporter` — dead code. | 🟡 Medium | ✅ X1: DONE — wired `clozeBasicToH5PBlanks` + `clozeToH5PBlanks` + `fillBlankToH5PBlanks` into `H5PExporter`. 3 switch cases added. 7 new tests (4 mapper + 3 integration). All 59 tests pass. Manual QA: valid H5P.Blanks ZIP. |
| 7.6 | Google Forms | Fully implemented, live OAuth + REST client — but explicitly **excluded** from both the `ExportFormat` type and the offline pipeline (`_UNSUPPORTED_GATEWAY_FORMATS`, `ExporterRegistry`). | 🟡 Medium | ✅ W3: Split as external publish target. NOT an offline file export format. Separate contract (`PublishTarget`) needed. |

**Verdict:** This is the second most consequential gap after the middleware
one. Two entire, non-trivial TS export implementations
(`gift-impl`/`h5p-impl`) sit fully built and **completely disconnected**
from the pipeline that teachers actually use. A teacher exporting GIFT/H5P
today gets a Python-generated skeleton, not the rich, question-type-aware
output the docs (and the real TS code) suggest exists. This should be
treated as a product-facing bug/gap, not a documentation nit.

**Grill resolution (§07):** ✅ X1 (done) + 📋 C1/D1/W3.
- H5P blanks: DONE. `cloze`, `cloze_mixed`, `fill_blank_wordbank` now produce valid `H5P.Blanks` ZIPs.
- GIFT/H5P: C1 — gateway route these formats through TS CLI subprocess (same as Anki/TSV path), replacing Python skeletons.
- QTI: D1 — explicit unsupported/error. No fake XML.
- `generateGift`/`generateH5P`/`generateQTI` public TS entrypoints: C3 — fix after C1. Not blocking.
- Google Forms: W3 — split into external publish target, not offline `ExportFormat`.
- `export_consensus_threshold` for Layer 6 export readiness: kept as required work item (see §04 O2).

---

## 08 — Common (contracts / schemas / branding)

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 8.1 | Theme kit count: "3 kits" | **4** kits exist — `high-contrast-dyslexia` (with an `accessibility` block) is undocumented. | 🟡 Medium | ✅ Part of J3: migrate `high-contrast-dyslexia` accessibility metadata to renderer theme, then delete. |
| 8.2 | "theme_*.css auto-generated" | True only for `common/branding`'s own CSS generation path. The renderer's actual runtime CSS comes from its own `themes/*.json`, generated fresh at load time — not from any pre-built CSS file. | 🟡 Medium | ✅ Docs fix: clarify CSS generation is runtime-only via renderer. |
| 8.3 | "theme.json is the single source of truth" (implied invariant) | Only half-true — two schema formats (flat vs 3-tier) both claim this role for different consumers, see 6.3. | 🟠 High | ✅ I1: Renderer `ThemeTokens` = single source of truth. common/branding deleted after migration. |

**Verdict:** Same root cause as 6.3, viewed from the schema side. Fixing
this requires picking **one** canonical theme format and either deleting the
other or making one generate the other — not a docs fix alone.

**Grill resolution (§08):** Merged with §06 I1/J3 — same fix. Renderer `ThemeTokens` canonical, common branding deleted after migration.

---

## 09 — Gateway

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 9.1 | Job store file name `teaching_pack_store.py` | Real job queue is `teaching_pack_job_store.py`. `teaching_pack_store.py` is a **different class** (`TeachingPackRunStore` — run CRUD + events + gates). | ⚪ Low | ✅ Docs fix: correct file names. |
| 9.2 | `RunEvent` location | Lives in `teaching_pack_models.py`, not `models.py`. | ⚪ Low | ✅ Docs fix: correct location. |
| 9.3 | Router file name `routers/teaching_packs.py` | Real file is `routers/teaching_pack_runs.py` (+ separate lifecycle/stream/preview files). | ⚪ Low | ✅ Docs fix: correct file name. |
| 9.4 | Gate count: "single teacher_approval gate" | The gate **registry** defines **6** named gates (`CLARIFICATION`, `CONTRACT_CONFIRMATION`, `SEARCH_PLAN_CONFIRMATION`, `BLUEPRINT_APPROVAL`, `CONTENT_APPROVAL`, `UNIT_APPROVAL`), each with its own allowed actions — a much richer HITL surface than one gate. | 🟠 High | ✅ R1: Document all 6 gates + allowed actions. Add sync rule: gate registry changes must update docs/API contract. |
| 9.5 | LLM proxy URL: `http://litellm:4000` | Actual default is `http://localhost:20228/v1` (9Router direct); LiteLLM is opt-in. See §10. | 🔴 Critical (shared with 10.x) | ✅ E1: Docs theo code. See §10 resolution. |

**Verdict:** 9.1–9.3 are pure renames, harmless once known. 9.4 matters
operationally — six independently-actionable gate types is a materially
different integration surface for anything building on top of the gateway
API (e.g. a Slack/Telegram approval bot) than "one gate."

**Grill resolution (§09):** ✅ R1.
- Document all 6 named gates in `teaching_pack_gate_registry.py` as the authoritative gate surface.
- Distinguish graph-level stage nodes (`teacher_approval` node) from gateway-level gate payloads (`content_approval`, `unit_approval`, etc.).
- Add rule: changes to `teaching_pack_gate_registry.py` must update docs/API contract/tests in same PR.

---

## 10 — Infra / Compose (LLM proxy topology)

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 10.1 | Proxy topology: `Agent → LiteLLM → 9Router` (primary path) | **Inverted.** Default dev/staging path is `Agent → 9Router` directly (`LLM_BASE_URL=http://localhost:20228/v1`). LiteLLM is optional, production-only, for budget control/fallback chains. | 🔴 Critical | ✅ E1: Docs theo code. Default = Agent → 9Router direct. LiteLLM optional/prod-only. |
| 10.2 | `services/proxy/config.yaml` | `Dockerfile.proxy` `COPY`s this file, but it **does not exist in the repo** — `docker compose build proxy` fails today. | 🔴 Critical | 🗑️ F1: Remove/park LiteLLM proxy from default compose. |
| 10.3 | `services/router/` | Does not exist. 9Router is an **external sidecar** (ports 20228/20128), not an in-repo containerized service — despite being central to every LLM call. | 🟠 High | ✅ Docs fix: remove `services/router/` from project structure docs. |
| 10.4 | Compose service list completeness | AGENTS.md omits `clickhouse`, `minio`, and the profile-gated `langfuse-worker`, all of which are present and load-bearing for the Langfuse stack. | 🟡 Medium | ✅ Docs fix: add missing services to compose docs. |

**Verdict:** 10.1 is the single highest-impact discrepancy in the whole
system — it inverts the direction of a core dependency. Anyone reasoning
about latency, cost control, or failover from AGENTS.md's diagram will
assume LiteLLM governs every call in dev/staging; it governs none of them.
10.2 is a live, reproducible build break and should be filed as a bug
independent of the doc question.

**Grill resolution (§10):** ✅ E1 + 🗑️ F1.
- Topology docs rewritten: dev/staging = `Agent → 9Router direct` (`LLM_BASE_URL=http://localhost:20228/v1`). LiteLLM = optional, prod-only, for budget control/fallback chains.
- LiteLLM proxy service removed from default compose (F1). Moved to separate profile or parked with TTL if kept for future use.
- `Dockerfile.proxy` + missing `services/proxy/config.yaml` build break resolved by removal.
- `services/router/` removed from docs (9Router is external sidecar, not in-repo).
- `.env.production`: fix env var name from `LLM_CLIENT_BASE_URL` to `LLM_BASE_URL` if prod LiteLLM path is still intended.
- Missing compose services (`clickhouse`, `minio`, `langfuse-worker`) added to docs.

---

## 11 — Web App

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 11.1 | `GATEWAY_URL` default | Client hardcodes `http://localhost:8101`; docker/gateway default is `:8001`. These two defaults **don't match out of the box**. | 🟡 Medium | ✅ U2: Keep `:8101` if intentional mapping/proxy exists. Document in docs/env comments. |
| 11.2 | Undocumented routes | `units/[parentRunId]` and the full-screen `(deck-editor)` route group both exist and are functional, but aren't mentioned in AGENTS.md and aren't linked from the dashboard sidebar (`units` has no nav entry despite the route existing). | 🟡 Medium | ✅ V3: Mark routes as intentional hidden/experimental. Add code/docs markers. No sidebar nav entry. |

**Verdict:** 11.1 is worth a quick config-parity check (is `:8101` actually
reachable against a `:8001`-published gateway, or is this a live local-dev
papercut?). 11.2 is a discoverability gap more than a technical one — the
route works, users just can't find it.

**Grill resolution (§11):** ✅ U2 + V3.
- `:8101` default kept as intentional. Docs/env comments explain the proxy/mapping. If no mapping found during implementation, revisit.
- `units/[parentRunId]` and `(deck-editor)` routes marked as intentional hidden/experimental via code comments and docs. No sidebar/nav entry added.
- If product promotes these routes later, then add navigation.

---

## 12 — Skills

| # | Ambiguity | Verdict | Severity | Resolution |
|---|-----------|---------|----------|------------|
| 12.1 | Implied: the 4 `skills/*.md` files are injected into agent prompts | They are **not**. `packages/agents/skills/registry.py`'s `SkillLoader` only maps curriculum/question-design skills; none of `blueprint-designer`, `pack-generator`, `artifact-reviewer`, `export-assistant` are registered or referenced by any code path. They are documentation-only artifacts referenced solely by `AGENTS.md` and an ADR. | 🔴 Critical | 🗑️ G3: Delete all 4 dead skill files. Remove all references from AGENTS.md. |
| 12.2 | `flashcard_deck` / Quizlet / Anki targets | Present in `pack-generator` skill spec but absent from AGENTS.md §9/§10's format lists. | 🟡 Medium | 🗑️ Gone with G3 delete of `pack-generator`. |
| 12.3 | Hard-block enumeration | `artifact-reviewer` lists `native_radio_inputs` and `unmanaged_js_runtime` as hard blocks; AGENTS.md's hard-block list omits both. | 🟡 Medium | 🗑️ Gone with G3 delete of `artifact-reviewer`. |

**Verdict:** 12.1 means the four "skills" are effectively **prose that no
agent ever reads** — whatever behavior AGENTS.md attributes to
"skill-guided" planning, rendering, review, or export is actually coming
from each agent's own `prompts/system.md`, not from these files. If the
intent was for skills to shape agent behavior, that wiring was never built.

**Grill resolution (§12):** 🗑️ G3 + 🔧 H3.
- Delete all 4 top-level skill files: `skills/blueprint-designer/`, `skills/pack-generator/`, `skills/artifact-reviewer/`, `skills/export-assistant/`.
- Remove all AGENTS.md references to these skills.
- Update any ADR references.
- Runtime skill system (`packages/agents/skills/`) remains but uses registry canonical.
- 🔧 H3: Refactor `SkillActivationMiddleware` to use `packages/agents/skills/registry.py` as single source of truth instead of hardcoding paths like `curriculum/ccss_math`. Currently middleware looks for files without `.md` extension → silently no-ops. Fix must resolve through registry + add `.md` extension or use registry's existing path map.

---

## Cross-cutting verdict: "registered but not wired" pattern

Four unrelated subsystems share the exact same failure mode — fully built,
zero runtime effect:

| Subsystem | Where it's "done" | Why it doesn't run | Resolution |
|---|---|---|---|
| Quality-tier middleware (6 layers: curriculum, readability, pedagogical, bias, coherence, LO-alignment) | `packages/agents/middleware/quality/*` | `middleware_runtime.py` never imports `QUALITY_GATE_CONSOLIDATED_MIDDLEWARE` | 🔧 Wire into `render_quality` as warning-only signals (see §03). |
| Real TS exporters (`gift-impl`, `h5p-impl`, `google-forms`) | `packages/exporters/src/*-impl/` | Gateway calls Python skeleton writers instead; `exportByFormat` stubs throw | 📋 Bridge gateway to TS CLI for GIFT/H5P (see §07 C1). QTI explicit unsupported (D1). Google Forms split as publish target (W3). H5P blanks DONE (X1). |
| Top-level prompt skills | `skills/*.md` | Not registered in `SkillLoader`'s `SKILL_MAP` | 🗑️ Delete all 4 files (see §12 G3). |
| Multi-judge consensus (Layer 4 ×3, Layer 6 ×3) | Config fields exist (`judge_n`, `export_consensus_threshold`) | Both hardcoded to single-judge MVP | ✅ Layer 4: `judge_n=3` enforced (see §04 N2). 📋 Layer 6: `export_consensus_threshold` wired in required work item (O2). |

**Recommended action for the team:** treat this list as a single backlog
item — "audit registered-but-unwired subsystems" — rather than four
separate bugs. The common root cause looks like incremental feature work
landing (exporters, quality middleware, skills, multi-judge) without a
corresponding wiring/integration PR, and no CI check currently catches
"registered symbol has zero call sites."

**Grill cross-cutting resolution:**
- Quality middleware: 🔧 wire as warning-only in `render_quality`.
- TS exporters: 📋 C1 bridge GIFT/H5P to CLI; ✅ X1 H5P blanks done; 🗑️ D1 QTI explicit fail; ✅ W3 Google Forms split.
- Skills: 🗑️ G3 delete.
- Multi-judge: ✅ N2 Layer 4 = 3 judges official; 📋 O2 Layer 6 = required work item.

---

## Cross-cutting verdict: "two sources of truth" pattern

| Domain | Source A | Source B | Currently authoritative | Resolution |
|---|---|---|---|---|
| Theming | `common/branding/kits/*/theme.json` (flat) | `packages/renderer/src/theme/themes/*.json` (3-tier `ThemeTokens`) | **B** at render time; A only feeds Python-side CSS gen, unused by the renderer | ✅ I1: **B** is canonical. 🗑️ J3: Migrate value from A then DELETE A. |
| LLM routing | `.env.example` default (`LLM_BASE_URL→9Router`) | `docker-compose.yml`'s optional `LITELLM_PROXY_URL` | **9Router direct** in dev/staging; LiteLLM only in prod, and only if explicitly enabled | ✅ E1: Docs rewritten to match code. 🗑️ F1: LiteLLM proxy removed from default compose. |
| Gate surface | AGENTS.md's single `teacher_approval` narrative | `teaching_pack_gate_registry.py`'s 6 named gates | **The registry** — it's what the gateway and web app actually implement against | ✅ R1: Docs rewritten to match registry. Sync rule added. |

**Recommended action:** for each pair, either (a) delete the losing source
and its generator, or (b) make the losing source auto-generate the winning
one so drift becomes structurally impossible instead of docs-dependent.

**Grill two-source-of-truth resolution:**
- Theming: canonical = renderer `ThemeTokens`. Common branding deleted after migration.
- LLM routing: canonical = code (9Router direct). LiteLLM proxy removed from default compose.
- Gate surface: canonical = registry (6 gates). Docs rewritten. Sync rule enforced.

---

## Grill session summary (2026-07-09)

### Completed in session

| # | Item | Action | Status |
|---|------|--------|--------|
| 1 | §07 H5P Blanks mapper | Wired `clozeBasicToH5PBlanks` + existing mappers into `H5PExporter`. Added 3 switch cases (`cloze`, `cloze_mixed`, `fill_blank_wordbank`). 7 new tests. All 59 tests pass. Manual QA: valid H5P.Blanks ZIP. | ✅ DONE |
| 2 | All 12 sections + cross-cutting | Grill session: 25 questions answered, all decisions documented above. | ✅ DONE |

### Pending work items (separate implementation required)

| # | Work item | Section | Priority |
|---|-----------|---------|----------|
| W1 | Wire `QUALITY_GATE_CONSOLIDATED_MIDDLEWARE` into `render_quality` (warning-only) | §03 | High |
| W2 | Bridge GIFT/H5P gateway to TS CLI subprocess | §07 C1 | High |
| W3 | Replace QTI skeleton with explicit unsupported/error | §07 D1 | Medium |
| W4 | Create `docs/runtime/teaching-pack-graph-contract.json` + snapshot test | §01 L2 | High |
| W5 | Update AGENTS.md: stage graph (10/12 stages), gates (6), models ("4omc"), scoring (sequential), topology (9Router direct) | §01-§12 | High |
| W6 | Migrate accessibility/typography/labels from `common/branding/kits` to renderer `ThemeTokens` then DELETE `common/branding/kits` | §06/§08 J3 | Medium |
| W7 | Remove/park LiteLLM proxy from default compose + fix `.env.production` env var name | §10 E1/F1 | High |
| W8 | Delete 4 dead top-level skill files + remove AGENTS.md references | §12 G3 | Low |
| W9 | Refactor `SkillActivationMiddleware` to use registry canonical | §12 H3 | Medium |
| W10 | Implement Layer 6 export readiness consensus using `export_consensus_threshold` | §04 O2 | Medium |
| W11 | Implement Playwright responsive validation for staging/prod | §05 T3 | Medium |
| W12 | Split Google Forms into `PublishTarget` contract (not `ExportFormat`) | §07 W3 | Low |

---

## Grill session gap analysis (found 2026-07-09)

### A. Decisions made but missing from W-list ("chốt xong rồi quên")

These items were resolved with ✅ in their section tables but never appeared
in the W-list. Without tracking, they will be forgotten.

| # | Item | Decision already recorded | Why it matters | Work item |
|---|------|--------------------------|----------------|-----------|
| A1 | **4.2 N2: `judge_n` 1→3** | ✅ N2 in §04 | Code change with 3× LLM cost/latency impact on every review call. Not a docs fix. | **W13** (High) |
| A2 | **4.4: `GRADE_LEVEL_COMPLEX_THRESHOLD` dead config** | 📋 in §04 | Defined but never read. Should wire or delete. | **W14** (Medium) |
| A3 | **6.1: `dompurify` dead dependency** | 🗑️ in §06 | `packages/renderer/package.json` still lists `dompurify@^3.0.0`. Real sanitizer is `sanitize-html`. | **W15** (Low) |
| A4 | **7.2 C3: `generateGift/H5P/QTI` stubs** | 📋 in §07 | Still throw `Not yet implemented`. After C1 bridge, this public API is inconsistent. | **W16** (Medium) |
| A5 | **10.x: `.env.production` wrong env var** | ✅ in §10 | Line 6: `LLM_CLIENT_BASE_URL=http://litellm:4000` — should be `LLM_BASE_URL`. Verified. | **W17** (Medium) |
| A6 | **11.1: `:8101` vs `:8001` investigation** | ✅ in §11 | Decision: "keep if mapping exists, revisit if not." But investigation not assigned. `apps/web/src/lib/api-client.ts:7` hardcodes `:8101`. | **W18** (Medium) |
| A7 | **W5 scope too narrow** | W5 says "stage graph, gates, models, scoring, topology" | Misses: 3.1 line-count, 4.1 package naming, 6.2/6.4 template+inlineCss, 8.2 CSS-gen, 9.1–9.3 gateway renames, 10.3–10.4 compose list, 7.4 GIFT coverage. | **W19** (Low) |
| A8 | **Sync rule enforcement** | Decisions in §01/§09/§02 for graph/gate/model sync | Only W4 creates a contract test for stage graph. Gate registry, model config, LLM topology have no enforceable sync mechanism → docs-vs-code drift will recur. | **W20** (Medium) |

### B. Risk items in existing decisions (should be addressed before implementation)

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| B1 | **W13 (judge_n=3) has no risk gate** | 3× cost/latency on every LLM review call. No rollback mechanism. No cost monitoring. | Add feature flag (`JUDGE_N` env var, default=3 with rollback to 1). Add cost dashboard check. Confirm `export_consensus_threshold` (W10/O2) is not confused with judge_n — they serve different gates (Layer 4 vs Layer 6). |
| B2 | **W1 (quality middleware) may recreate the same bug** | Wiring middleware to write signals into state without a consumer reading those signals = "runs but unused" — same as "registered but not wired." | Add acceptance criterion: at least one consumer (routing, healer, or UI approval) must read the quality signals before W1 is considered done. |
| B3 | **Exporters API dual-entrypoint conflict after C1** | C1 bridges gateway→TS CLI (subprocess). C3 leaves public `exportByFormat`/`generateGift`/`generateH5P`/`generateQTI` as `NotImplemented` stubs. Two entrypoints for same subsystem, one working (CLI) one broken (public API). | Add JSDoc/code comment marking which entrypoint is "official" for each path. W16 (C3) must at minimum mark public stubs as deprecated or route to real impl. |
| B4 | **11.1 investigation unassigned** | Decision: "keep :8101 if mapping exists." But nobody has verified whether a reverse proxy maps 8101→8001. | W18 must confirm actual mapping. If no mapping exists, decision reverts to W17-style config parity fix. |

### Updated W-list (W13–W20)

| # | Work item | Section | Priority |
|---|-----------|---------|----------|
| W13 | Change `GateConfig.judge_n` from 1→3, add `JUDGE_N` env var override for rollback, add cost/latency monitoring gate, confirm `export_consensus_threshold` is separate concept | §04 N2 | High |
| W14 | Wire or delete `GRADE_LEVEL_COMPLEX_THRESHOLD` in `age_checker.py` (defined line 13, never read by `check_age_appropriateness`) | §04 4.4 | Medium |
| W15 | Remove dead `dompurify` dependency from `packages/renderer/package.json` | §06 6.1 | Low |
| W16 | Fix public TS entrypoints (`generateGift`/`generateH5P`/`generateQTI`): route to real impl or mark deprecated with JSDoc, after C1 bridge is done | §07 C3 | Medium |
| W17 | Fix `.env.production` line 6: `LLM_CLIENT_BASE_URL` → `LLM_BASE_URL` | §10 | Medium |
| W18 | Investigate `:8101` vs `:8001`: confirm whether reverse proxy maps 8101→8001, document finding, fix if no mapping exists | §11 11.1 | Medium |
| W19 | Expand W5 docs-fix checklist to include all small fixes: 3.1 line-count, 4.1 package naming, 6.2/6.4 template+inlineCss, 8.2 CSS-gen, 9.1–9.3 gateway renames, 10.3–10.4 compose list, 7.4 GIFT coverage | §01–§12 | Low |
| W20 | Expand test-enforced contract (W4 pattern) to gate registry (§09 9.4), model config (§02 2.x), and exporter format matrix (§07 7.x) | §01/§02/§07/§09 | Medium |

### Verification notes

All gap claims verified against source code:

- **A1 (N2)**: `packages/agents/config/gate_config.py` `judge_n=1` confirmed.
- **A2 (4.4)**: `packages/agents/gates/presentation/age_checker.py:13` defines `GRADE_LEVEL_COMPLEX_THRESHOLD`, line 21 `check_age_appropriateness` never reads it — confirmed dead.
- **A3 (6.1)**: `packages/renderer/package.json:24` lists `"dompurify": "^3.0.0"` — confirmed dead dependency.
- **A5 (10.x)**: `.env.production:6` reads `LLM_CLIENT_BASE_URL=http://litellm:4000` — confirmed wrong env var name (config reads `LLM_BASE_URL`).
- **A6 (11.1)**: `apps/web/src/lib/api-client.ts:7` hardcodes `http://localhost:8101` — confirmed. No reverse proxy evidence found in compose/docs.
