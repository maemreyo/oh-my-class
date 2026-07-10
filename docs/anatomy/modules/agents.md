# Module: agents

**Path:** `packages/agents`
**Role:** LangGraph multi-agent pipeline — the orchestration engine that takes a teacher's lesson request and produces a complete, quality-gated teaching pack through a 10-stage state machine.

## Public interface

- `build_teaching_pack_graph(checkpointer, store, quality_gate)` → compiled LangGraph StateGraph (`teaching_pack/graph.py:32`)
- `teaching_pack_thread_config(run_id)` → LangGraph configurable dict (`teaching_pack/graph.py:152`)
- `TeachingPackState` — the full pipeline state TypedDict with ~55 fields (`teaching_pack/nodes.py`)
- `AgentRuntime` — LLM call orchestration with retry, tags, temperature ramping (`runtime.py`)
- `emit_run_event()` / `subscribe()` — in-memory event bus for SSE (`events.py`)
- `get_checkpointer(environment)` → MemorySaver | SqliteSaver | PostgresSaver (`checkpointer.py`)
- `ORDERED_MIDDLEWARE_LIST` — 23 middleware layers in fixed execution order (`middleware/registry.py:36`)
- `SKILL_MAP` — 6 curriculum skill definitions (`skills/registry.py`)
- `PromptCompiler` / `PromptRegistry` — versioned prompt governance (`prompts/`)

## Internal structure

### teaching_pack/ (42 files) — The Authoritative Pipeline

- `graph.py` — `build_teaching_pack_graph()`: wires stage nodes with conditional edges. Feature-flagged: 10 stages default, 12 with component strategist. Conditional routes: `route_after_triage` → `unit_planning` or `preplanning_search`; `route_after_teacher_approval` → `artifact_workflow` or `export_finalize` (with scoped rejection logic); `route_after_compliance_gate` → `teacher_approval` or `artifact_workflow`; `route_after_render_quality` → `planning_blueprint`, `post_blueprint_research`, `artifact_workflow`, `teacher_approval`, or `compliance_gate`
- `stages.py` — `StageEnum` (StrEnum, 15 values): `SETUP_CONTRACT`, `TRIAGE`, `UNIT_PLANNING`, `UNIT_APPROVAL`, `UNIT_PREP`, `PREPLANNING_SEARCH`, `PLANNING_BLUEPRINT`, `PROVISIONAL_COMPONENT_STRATEGY`, `POST_BLUEPRINT_RESEARCH`, `FINALIZE_COMPONENT_STRATEGY`, `ARTIFACT_WORKFLOW`, `RENDER_QUALITY`, `COMPLIANCE_GATE`, `TEACHER_APPROVAL`, `EXPORT_FINALIZE`. Two presets: `TEACHING_PACK_STAGES` (10 default) and `TEACHING_PACK_STAGES_WITH_COMPONENT_STRATEGY` (12, adds `PROVISIONAL_COMPONENT_STRATEGY` and `FINALIZE_COMPONENT_STRATEGY`). Note: `UNIT_PLANNING`/`UNIT_APPROVAL`/`UNIT_PREP` are NOT in either preset tuple — they are added conditionally by `build_teaching_pack_graph()` based on triage routing.
- `nodes.py` — `make_stage_node()` factory dispatching to handler functions; `TeachingPackState` TypedDict (~55 fields); all routing functions for conditional edges including `_unit_approval()`, `route_after_triage()`, `route_after_teacher_approval()` (checks `component_strategy_plan`, `is_scoped_teacher_action`, `has_scoped_section_edit`, `_scoped_reactions`), `route_after_compliance_gate()`
- `ports.py` — 8 Protocol interfaces (`RunStore`, `QualityGate`, `ArtifactRenderer`, `LLMTransport`, etc.) decoupling the graph from infrastructure
- `config.py` — `TeachingPackConfig` (pydantic-settings): parallelism, timeouts, max attempts
- `triage.py` — Heuristic + LLM single-lesson vs multi-session unit routing
- `compliance.py` — `compliance_gate_state()`: deterministic hard-block checks (answer-key, PII, HTML)
- `quality.py` — `quality_issues()`: schema validation, placeholder detection, answer-key separation, pack coherence
- `quality_routing.py` — `route_after_render_quality()`: routes by issue type; `quality_recovery_route()` maps `factual_uncertainty` → `post_blueprint_research`, `not_aligned_with_objectives`/`vietnamese_difficulty` → `planning_blueprint`, default → `artifact_workflow`
- `quality_runtime.py` — `render_quality()`: orchestrates Layer 1-4 quality checks
- `artifact_fanout.py` — Parallel artifact generation via LangGraph `Send` with wave-based dependency ordering (`_DEPENDENCIES`, `_WAVES`)
- `exporters.py` — `ExporterRegistry`: HTML/GIFT/H5P/QTI/Anki/PPTX dispatch
- `snapshots.py` — `build_snapshot()`: renders artifacts to standalone HTML (teacher + student views)
- `store.py` — PostgresStore factory for cross-run memory with TTL
- `middleware_runtime.py` — 4 middleware groups: entry, generation-context, gate, quality-consolidated
- `scoped_regeneration.py` — Scoped section/block edit application on teacher rejection

### sub_agents/ (9 agents)

| Agent | Role | Key contracts |
|-------|------|---------------|
| `planner` | UbD lesson plan generation (Gagne 9-event) | `LessonPlan`, `LessonSequence` |
| `researcher` | FACT-protocol web research + grounding | `ResearchBundle` |
| `content_creator` | ArtifactContent generation (hierarchical or sequential) | `ArtifactContent` |
| `reviewer` | LLM-as-Judge via AdaptiveJudge (G-Eval, 3 judges) | `JudgeOutput` |
| `unit_planner` | Multi-session unit sequencing + critique | `LessonSequence` |
| `diagnostician` | Student performance diagnostics (BKT) | `DiagnosticReport` |
| `coherence_judge` | Cross-artifact coherence check | skeleton |
| `practice_generator` | Drill/practice set generation | minimal |
| `roadmap_agent` | Curriculum roadmap generation | `RoadmapContent` |

### middleware/ (23 layers)

Ordered execution: `InputSanitization(1)` → `TokenBudget(2)` → `ThreadData(3)` → `Uploads(4)` → `ContentSafety(5)` → `LLMErrorHandling(6)` → `Guardrail(7)` → `TeacherAuditLog(8)` → `SafetyFinishReason(9)` → `DynamicContext(10)` → `SkillActivation(11)` → `TokenUsage(12)` → `Title(13)` → `Memory(14)` → `SystemMessageCoalescing(15)` → `CurriculumAlignment(16)` → `ReadabilityLevel(17)` → `PedagogicalQuality(18)` → `BiasDetection(19)` → `ArtifactCoherence(20)` → `LearningObjectiveAlignment(21)` → `SequenceConsistencyValidator(22)` → `Clarification(23)` — **Clarification must always be last (INVARIANT-08)**.

### gates/ (HITL implementations)

`blueprint_approval`, `content_approval`, `schema_validator`, `content_reviewer`, `llm_judge`, `export_readiness`, `fact_check/`, `presentation/`

### healing/ (self-healing system)

Escalation ladder: `retry(1st)` → `rewrite(2nd)` → `reroute(3rd)` → `replan(4th)` → `escalate(>4)`. Includes `CircuitBreaker` (run-scoped + provider-scoped, Redis-backed).

### llm/ (LLM routing)

`complete_json_chat()` main call path with streaming transport policy, Langfuse tracing, event emission, prompt gate enforcement.

### tools/ (agent tool definitions)

`web_search`, `web_fetch` (via 9Router sidecar), `read_file`, `write_file`. Access matrix: planner=web_search+read_file, researcher=web_search+web_fetch+read_file, content_creator=read_file+write_file.

### config/ (model routing)

3-tier model assignment: strong (`MODEL_STRONG_DEFAULT`), medium (always "4omc"), fast (`MODEL_FAST_DEFAULT`). Feature flags: `topic_decomposition_v1`, `vocabulary_batch_v1`, `component_strategist_v1`.

### Other

- `prompts/` — Versioned prompt modules with SHA-256 content hashes, overlay governance, drift detection
- `skills/` — 6 curriculum skills (CCSS Math/ELA, VN Ministry 2018, HSA Exam Prep, Bloom Taxonomy, Zamery Pack)
- `observability/` — Langfuse tracing (degrades to no-op)
- `slide_deck_engine/` — Deterministic slide deck generation with phases, policies, quality checks
- `inverse_thinking_pipeline.py` — Alternative pedagogy projection
- `kt_engine.py` — Knowledge Tracing (BKT) update per student per KC

## Depends on

- **`contracts`** — imports 147+ Pydantic models: `LessonPlan`, `ResearchBundle`, `ArtifactContent`, `RunContract`, `ArtifactWorkflowState`, `QualityReport`, `LessonSequence`, `InverseThinkingPack`, etc. (`teaching_pack/nodes.py`, `sub_agents/*/nodes.py`)
- **`quality`** — imports `AdaptiveJudge`, `check_artifact_answer_key_leakage`, `html_hard_blocks`, `detect_pii`, `ComplianceResultDict` (`healing/`, `gates/`, `middleware/safety/`)
- **`renderer`** — imports `renderArtifact()`, `SlideDeckData` projection (`teaching_pack/snapshots.py`, `slide_deck_engine/`)
- **`methodologies`** — imports `InverseThinkingProjection` (`inverse_thinking_pipeline.py`)
- **`gateway`** — imports `services.gateway.events`, `services.gateway.teaching_pack.stages` (only in `teaching_pack/store.py` for PostgresStore)
- external: `langgraph>=1.0.0` (StateGraph, checkpointer, interrupt, Send)
- external: `httpx>=0.27.0` (9Router HTTP transport)
- external: `langchain-openai>=1.3.3`
- external: `networkx>=3.5` (graph algorithms)
- external: `pydantic-settings>=2.14.2`
- external: `langfuse>=2.0.0` (optional tracing)

## Used by

- **`gateway`** — imports `build_teaching_pack_graph`, `TeachingPackState`, `teaching_pack_thread_config` at startup (`services/gateway/main.py:150-155`, `teaching_pack_executor.py`)
- **`tests`** — imports teaching pack graph, nodes, stages, artifact fan-out (`tests/e2e/`, `tests/integration/`, `tests/security/`)
- **`scripts`** — imports agents config and testing utilities (`scripts/`)

## Data & side effects

- Reads/writes: PostgreSQL via SQLAlchemy (state persistence), Redis (circuit breaker, teaching session pub/sub)
- Network calls: 9Router sidecar (`http://localhost:20128/v1`) for LLM and web search/fetch (sync/async)
- Config/env vars: `MODEL_*`, `FEATURE_*`, `MAX_TOKENS_*`, `NINEROUTER_*`, `OMC_ENVIRONMENT`, `DATABASE_URL`, `REDIS_URL`

## Notes / discrepancies vs existing docs

- AGENTS.md §4.1 claims model names `deepseek-v4-flash` / `gpt-5.4`; the code uses `"4omc"` everywhere with tier aliases (all default to "4omc" unless env vars override). The model source of truth is `config/models.py`, not AGENTS.md.
- AGENTS.md §4.4 describes Reviewer as calling LLM directly; it actually constructs `AdaptiveJudge(num_judges=gate_config.judge_n)` and delegates through `AgentRuntime` with multi-judge dispatch.
- AGENTS.md §8.5 lists 13 template files; the actual count in `templates/pages/` is 13 page templates plus 43 component templates plus 10 Artifact UI templates.

---

_Traced from source on 2026-07-10. Files examined in depth: all 434 files in packages/agents, prioritized by reference count and size. Key entry points: teaching_pack/graph.py, teaching_pack/nodes.py, middleware/registry.py._
