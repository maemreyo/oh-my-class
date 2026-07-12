# Module: agents

**Path:** `packages/agents`
**Role:** LangGraph multi-agent pipeline that orchestrates teaching-pack generation through a 10-stage (default) or 12-stage (component-strategist) StateGraph, with 23-layer middleware, 6-layer quality gates, self-healing, and HITL approval gates.

## Public interface

### Graph construction and execution
- `build_teaching_pack_graph(checkpointer, store, quality_gate, content_store, ...)` — builds the compiled LangGraph StateGraph. Entry point for the entire pipeline. (`teaching_pack/graph.py:32`)
- `teaching_pack_thread_config(run_id) -> LangGraphRunnableConfig` — returns thread config with `thread_id` and `max_concurrency`. (`teaching_pack/graph.py:168`)
- `TeachingPackState` — the canonical LangGraph state TypedDict used by all stage nodes. (`teaching_pack/nodes.py:61`)

### Stage definitions
- `TeachingPackStage` (alias for `StageEnum`) — 15-value StrEnum of all possible stage names. (`teaching_pack/stages.py:9`)
- `teaching_pack_stages(component_strategy_enabled) -> tuple[StageEnum, ...]` — returns the 10-stage or 12-stage tuple based on feature flag. (`teaching_pack/stages.py:71`)
- `TEACHING_PACK_STAGES` — default 10-stage tuple. (`teaching_pack/stages.py:42`)
- `TEACHING_PACK_STAGES_WITH_COMPONENT_STRATEGY` — 12-stage variant. (`teaching_pack/stages.py:55`)

### Protocol ports (boundary contracts)
- `TeachingPackGraph` — LangGraph execution boundary protocol. (`teaching_pack/ports.py:62`)
- `QualityGate` — artifact quality check boundary. (`teaching_pack/ports.py:125`)
- `ArtifactRenderer` — HTML rendering boundary. (`teaching_pack/ports.py:97`)
- `SearchFetchClient` — search/fetch boundary. (`teaching_pack/ports.py:89`)
- `LLMTransport` — structured model call boundary. (`teaching_pack/ports.py:74`)
- `NotificationChannel` — teacher/admin notification boundary. (`teaching_pack/ports.py:110`)
- `RunStore` — run metadata persistence boundary. (`teaching_pack/ports.py:17`)
- `EventWriter` — compact event persistence boundary. (`teaching_pack/ports.py:29`)
- `ArtifactSnapshotStore` — rendered snapshot cache boundary. (`teaching_pack/ports.py:42`)
- `RunExecutor` — queued run execution boundary. (`teaching_pack/ports.py:50`)

### Runtime
- `AgentRuntime` — LLM call wrapper with retry, temperature decay, and metadata tagging. (`runtime.py:47`)
- `AgentRuntimeConfig` — configuration for agent, model, retries, temperature. (`runtime.py:34`)

### Event bus
- `emit_run_event(run_id, event_type, data)` — append event + notify SSE subscribers. (`events.py:79`)
- `publish_event(event: ObservabilityEvent)` — low-level publish. (`events.py:84`)
- `ObservabilityEvent` — Pydantic model for typed pipeline events. (`events.py:52`)
- `subscribe(run_id) -> Queue` / `unsubscribe(run_id, queue)` — SSE subscription management. (`events.py:115`)

### Checkpointer factory
- `get_checkpointer(environment, *, exit_stack=None, **kwargs)` — creates MemorySaver/SqliteSaver by environment, or (production) an `AsyncPostgresSaver` entered into the caller's `AsyncExitStack`. (`checkpointer.py:22`, now `async def`.)
- **Real bug found and fixed this session (#123 OPS-10):** the teaching-pack graph's nodes are all `async def` and the graph is invoked via `ainvoke`/`astream` (`teaching_pack_executor.py:125,136`). Production previously used the *sync* `langgraph.checkpoint.postgres.PostgresSaver`, whose async methods (`aget_tuple`, `aput`, ...) are unimplemented stubs that raise `NotImplementedError` — confirmed by reproduction (`AsyncPostgresSaver` vs sync `PostgresSaver` against a real local Postgres). Worse, the old code called `PostgresSaver.from_conn_string(connection_string)` (a `@contextmanager`) without entering it, so `app.state.checkpointer` for production was actually an unentered `_GeneratorContextManager`, not a usable saver — and `services/gateway/main.py` never even passed a `connection_string`, so this path would have raised `ValueError` at startup on first real production deployment. No test exercised this before (`get_checkpointer` had zero test coverage). Fixed: production now builds a real `AsyncPostgresSaver`, entered into an `AsyncExitStack` owned by `main.py`'s `lifespan()` (which switched from sync `contextlib.ExitStack` to `contextlib.AsyncExitStack` to support this). Covered by `packages/agents/tests/test_checkpointer.py` (real Postgres, asserts `aget_tuple` doesn't raise) and `tests/resilience/test_checkpoint_resume_mid_stage_kill.py` (real `AsyncPostgresSaver` + real graph: runs `setup_contract`, discards the compiled graph entirely to simulate a worker kill, rebuilds a fresh graph against the same checkpointer/thread_id, resumes, and asserts `setup_contract` is not re-executed — the checkpoint-resume acceptance item #123 previously left unverified).

### Healing
- `healing_node(state)` — graph node that delegates to `HealingOrchestrator`. (`healing/orchestrator.py:71`)
- `HealingOrchestrator` — selects healing strategy (retry/rewrite/reroute/replan/escalate) by fail count and type. (`healing/orchestrator.py:14`)
- `CircuitBreaker` — per-run or per-provider circuit breaker with Redis-backed persistence. (`healing/circuit_breaker.py:77`)

### Middleware
- `BaseMiddleware` — ABC with `before_model`/`after_model` hooks. (`middleware/base.py:38`)
- `ORDERED_MIDDLEWARE_LIST` — 23 middleware in execution order. (`middleware/registry.py:36`)
- `RUN_ENTRY_MIDDLEWARE`, `GENERATION_CONTEXT_MIDDLEWARE`, `GATE_LAYER_MIDDLEWARE`, `QUALITY_GATE_CONSOLIDATED_MIDDLEWARE` — middleware subsets for specific pipeline phases. (`middleware/registry.py:64-90`)

### Configuration
- `MODELS` — `ModelAssignments` singleton (14 model slots, 3 tiers, env-overridable). (`config/models.py:150`)
- `MAX_TOKENS` — `MaxTokensConfig` singleton (per-agent token budgets). (`config/models.py:151`)
- `NINEROUTER` — `NinerouterConfig` singleton (search/fetch config). (`config/models.py:152`)
- `features() -> FeatureFlags` — cached feature flags from env. (`config/features.py:32`)
- `GateConfig` — all quality gate thresholds (Pydantic Settings, `GATE_` prefix). (`config/gate_config.py:12`)

### Compliance gate
- `compliance_gate_state(state)` — deterministic compliance checks (answer key leakage, PII, HTML hard blocks). (`teaching_pack/compliance.py:39`)
- `evaluate_compliance(state) -> ComplianceResult` — core evaluation logic. (`teaching_pack/compliance.py:65`)

### Quality routing
- `route_after_render_quality(state)` — conditional routing after quality gate (5 destinations). (`teaching_pack/quality_routing.py:27`)
- `route_after_compliance_gate(state)` — routes to teacher_approval or artifact_workflow. (graph wiring: `graph.py:139`)
- `route_after_teacher_approval(state)` — routes to export_finalize or artifact_workflow. (graph wiring: `graph.py:115`)
- `route_after_triage(state)` — routes to plan_unit or generate_pack path. (graph wiring: `graph.py:83`)
- `route_after_unit_approval(state)` — routes to unit_prep or back to unit_planning. (graph wiring: `graph.py:103`)
- `route_after_artifact_workflow(state)` — fan-out to render_quality or generate_one_artifact. (graph wiring: `graph.py:122`)

## Internal structure

```
packages/agents/
├── teaching_pack/             # Authoritative stage graph
│   ├── graph.py               # build_teaching_pack_graph — StateGraph assembly
│   ├── stages.py              # StageEnum (15 values), teaching_pack_stages()
│   ├── nodes.py               # make_stage_node() dispatch, all stage node impls
│   ├── ports.py               # Protocol boundaries (10 protocols)
│   ├── config.py              # TeachingPackConfig (parallelism, etc.)
│   ├── quality_routing.py     # route_after_render_quality (5-way conditional)
│   ├── quality.py             # Quality gate helper functions
│   ├── quality_runtime.py     # Runtime quality evaluation
│   ├── compliance.py          # Deterministic compliance gate (answer key, PII, HTML)
│   ├── content_orchestrator.py # ArtifactContentStore abstraction (persist/persist_result/read_projections/read_answer_set); InMemory + LangGraph adapters. Persistence port only -- NOT the ADR-053 Content Orchestrator (see module docstring). SpecialistResult (#464) is an alias of ArtifactPersistenceResult
│   ├── artifact_fanout.py     # Artifact fan-out routing and generation; wave/dependency structure sourced from common.contracts.dependency_plan.DEFAULT_DEPENDENCY_PLAN (#464), not local tuples. `_payload()` now also threads `subject`/`grade_band` (#464, this session) into GenerateOneArtifactPayload from `state["contract"]` -- `grade_band` normalized via `common.contracts.grade_band.grade_band_for_label`, falling back to GRADES_3_5 for an unparseable/missing label rather than leaving it ambiguous
│   ├── generate_one_artifact.py # Single artifact generation node; dispatches through specialist_capability.resolve_specialist_capability (#464) -- raises UnsupportedArtifactCapabilityError when resolution.status == "unsupported". OrchestratorRequest (#464) is an alias of GenerateOneArtifactPayload. `subject`/`grade_band` (NotRequired, #464 this session) now flow through the payload but are not yet read/used inside this function -- see content_coverage_resolution.py's note below for the remaining wiring gap
│   ├── specialist_capability.py # #464: typed 3-way capability resolution (supported/degraded/unsupported) -- CapabilityResolution, resolve_specialist_capability(); the "no silent generic fallback" boundary. Also SPECIALIST_CAPABILITIES: per-artifact-type declared payload_kind/answer_bearing (deliberately no subject/grade claims -- the 10 registered specialists don't branch on either); ANSWER_SET_ARTIFACT_TYPES is generate_one_artifact.py's own SSOT for which types derive an AnswerSet; SPECIALIST_FAMILIES groups every artifact type into ADR-053's five named families (lesson_design/assessment/practice/synthesis/presentation)
│   ├── content_coverage_resolution.py # #464 (new this session): resolve_content_coverage() composes specialist_capability's code-capability resolution with subject_capability_pack.py's curriculum coverage into one joint (artifact_type, subject, grade_band) decision -- a separate module, not a change to specialist_capability.py, since that module's own docstring says declaring subject/grade specificity per specialist would be fabricated. Tested against the four real capability-pack fixtures (common/component_strategy_knowledge/capabilities/). **Not yet wired to a live caller**: `GenerateOneArtifactPayload` now carries `subject`/`grade_band` (threaded by artifact_fanout.py's `_payload`, this session), but `generate_one_artifact.py` doesn't call this resolver yet -- deliberately deferred, since there's no production capability-pack registry/loader yet (only test fixtures), and deciding how a "degraded" (uncertified) result should surface to teachers/observability is a product decision, not one this session should make unilaterally
│   ├── (guard test, `tests/test_no_undeclared_content_creator_fallback.py`) # #464's own "Required Tests" list names this guard directly. Found a genuine second real caller while writing it: `nodes.py::_rollback_artifact_workflow` (lines ~475-515) calls `content_creator_node` for every artifact type unconditionally -- the named legacy V1 path, only reached when `OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1` is explicitly set (`artifact_send_fanout_v1_enabled()` defaults `True`, so the new fanout/registry path is the production default). The guard asserts `content_creator_node` is referenced from exactly two files -- `generate_one_artifact.py` (the flag-gated fallback) and `nodes.py` (the flag-gated rollback) -- and fails on any third site
│   ├── healing_runtime.py     # Healing integration for teaching-pack pipeline
│   ├── scoped_repair.py       # Scoped regeneration on rejection
│   ├── scoped_repair_models.py # Repair model definitions
│   ├── gate_trust.py          # Teacher trust score computation
│   ├── triage.py              # Request triage (unit vs children)
│   ├── vocabulary_batch_orchestrator.py # Vocabulary batch workflow
│   ├── vocabulary_input_normalizer.py # Input normalization
│   ├── vocabulary_snapshot.py # Vocabulary snapshot management
│   ├── component_strategy_stage.py # Component strategy generation
│   ├── component_strategy_rollout.py # Feature-flagged rollout logic
│   ├── strategy_quality.py    # Strategy quality validators
│   ├── strategy_quality_events.py # Strategy quality observability
│   ├── teacher_memory.py      # Cross-run teacher memory (LangGraph store)
│   ├── subject_packs/         # Subject-specific question builders
│   └── specialists/           # Artifact-type specialists
├── sub_agents/                # 9 sub-agent implementations
│   ├── planner/               # Lesson planning (UbD, staged engine, curriculum coverage)
│   ├── researcher/            # Research gathering (lexical grounding, evidence)
│   ├── content_creator/       # Content generation (hierarchical, semantic anchors)
│   ├── reviewer/              # Quality review (live quality gate, AdaptiveJudge)
│   ├── unit_planner/          # Unit-level sequencing (critique, repair, observability)
│   ├── diagnostician/         # Student performance diagnostics
│   ├── roadmap_agent/         # Curriculum roadmap generation
│   ├── practice_generator/    # Drill/practice set generation (semantic anchors)
│   └── coherence_judge/       # Cross-artifact coherence check
├── middleware/                 # 23-layer middleware chain
│   ├── base.py                # BaseMiddleware ABC, MiddlewareState, MiddlewareContext
│   ├── registry.py            # Ordered middleware list, phase subsets
│   ├── context/               # DynamicContext, Memory, SkillActivation, Title, TokenUsage, SystemMessageCoalescing
│   ├── quality/               # Curriculum, Readability, Pedagogical, Bias, ArtifactCoherence, LOAlignment
│   ├── safety/                # ContentSafety, Guardrail, InputSanitization, LLMErrorHandling, SafetyFinishReason, TeacherAuditLog, ThreadData, TokenBudget, Uploads
│   └── terminal/              # Clarification (always last, order=23)
├── gates/                     # Quality gate implementations
│   ├── state.py               # GateState TypedDict
│   ├── content_reviewer.py    # Content quality review gate
│   ├── llm_judge.py           # LLM-as-Judge (AdaptiveJudge)
│   ├── presentation/          # HTML validation, answer key guard
│   ├── export_readiness.py    # Export readiness gate
│   └── gate_01_blueprint.py, gate_02_content_approval.py # Legacy gate nodes
├── healing/                   # Self-healing system
│   ├── orchestrator.py        # HealingOrchestrator (strategy selection)
│   ├── circuit_breaker.py     # CircuitBreaker (per-run, per-provider)
│   ├── strategies/            # retry, rewrite, reroute, replan, escalate
│   ├── redis_breaker_store.py # Redis-backed breaker state persistence
│   └── html_healer.py         # HTML-specific healing
├── config/                    # Configuration
│   ├── models.py              # ModelAssignments, MaxTokensConfig, NinerouterConfig
│   ├── features.py            # FeatureFlags (7 flags)
│   ├── gate_config.py         # GateConfig (all thresholds)
│   └── model_drift.py         # Model snapshot and drift detection
├── events.py                  # In-memory event bus (SSE/observability)
├── runtime.py                 # AgentRuntime, AgentRuntimeConfig
├── checkpointer.py            # LangGraph checkpointer factory
├── llm/                       # LLM client wrappers
├── prompts/                   # Prompt compiler
├── tools/                     # LLM tools (web_search, read_file, write_file, ninerouter_web)
├── observability/             # Langfuse tracing integration
├── quality/                   # Internal quality checks (unit_coherence)
├── slide_deck_engine/         # Slide deck generation engine (~15 files)
├── effectiveness/             # Student effectiveness tracking (MoET export)
├── skills/                    # Skill loader/registry
├── nodes/                     # Legacy node implementations (NodeState, finalize, etc.)
└── grounding/                 # Knowledge grounding
```

## Depends on

- **`contracts`** — 157 imports across 125 files; Pydantic models for all pipeline stages
- **`quality`** — 17 imports across 14 files; compliance policy, PII detection, component gates
- **`llm-client`** — 4 imports across 3 files; LLM transport layer
- **`methodologies`** — 1 import; inverse thinking pipeline

### common/contracts (157 imports across 125 files) — CONFIRMED

The primary dependency. Agents imports Pydantic models that define the data contracts between pipeline stages and across module boundaries.

**Key imports by contract:**
- `common.contracts.artifact` → `ArtifactContent` — `teaching_pack/nodes.py:5`, `teaching_pack/content_orchestrator.py:8`, `teaching_pack/generate_one_artifact.py:8`, `sub_agents/content_creator/nodes.py:12`, `sub_agents/content_creator/hierarchical.py:7`
- `common.contracts.lesson_plan` → `LessonPlan`, `MethodologyMetadata` — `sub_agents/planner/nodes.py:13`, `sub_agents/planner/staged_engine.py:7`, `sub_agents/planner/lesson_critic.py:6`
- `common.contracts.quality` → `QualityFailureClass`, `QualityIssue`, `ArtifactQualityReport` — `teaching_pack/compliance.py:9`, `teaching_pack/quality_runtime.py:6`, `teaching_pack/scoped_repair.py:5`, `sub_agents/reviewer/live_quality_gate.py:8`
- `common.contracts.run_contract` → `JsonObject`, `RunContract`, `DecompositionIntent` — `teaching_pack/ports.py:13`, `teaching_pack/triage.py:6`, `slide_deck_engine/deck_shape.py:28`
- `common.contracts.research_bundle` → `ResearchBundle` — `sub_agents/researcher/nodes.py:15`
- `common.contracts.slide_deck` → `SlideDeckData`, `SlideDeckSlide`, `PedagogicalRole` — `slide_deck_engine/models.py:7`, `slide_deck_engine/deck_shape.py:29`, `slide_deck_engine/pedagogical_components.py:58`
- `common.contracts.vocabulary_batch` → `SemanticAnchorCluster`, `PracticeSet`, `NormalizedVocabularyCluster` — `sub_agents/practice_generator/semantic_anchor.py:9`, `sub_agents/content_creator/semantic_anchor_synthesis.py:8`, `teaching_pack/vocabulary_batch_orchestrator.py:10`
- `common.contracts.lesson_sequence` → `LessonSequence`, `SessionPlan`, `BloomLevel` — `sub_agents/unit_planner/nodes.py:7`, `sub_agents/unit_planner/sequence_critic.py:7`, `middleware/sequence_consistency_validator.py:9`
- `common.contracts.component_strategy` → `ComponentStrategyRequest` — `teaching_pack/component_strategy_stage.py:5`
- `common.contracts.outcome` → `StudentAttempt`, `StudentKCState` — `kt_engine.py:8`, `effectiveness/moet_export.py:6`
- `common.contracts.grade_band` → `GradeBand`, `grade_band_for_label`, `FlashcardGradeBand`, `flashcard_grade_band` — `teaching_pack/subject_packs/math_question_builder.py:16`, `teaching_pack/specialists/quiz_specialist.py:8`, `teaching_pack/specialist_registry.py:12` (#462: replaced the specialist registry's own elementary/middle/high regex with this canonical adapter), `teaching_pack/specialists/flashcard_deck_specialist.py:17`
- `common.contracts.answer_set` → `AnswerSet`, `derive_answer_key_artifact`, `derive_answer_set` — `teaching_pack/generate_one_artifact.py:7` (drives the #463 V2 flow: `generate_one_artifact` derives an `AnswerSet` for quiz/drill/exit_ticket, then calls `content_store.persist_result(...)` so the store — not the student projection — is the only place the answer set is retrievable via `read_answer_set`)
- `common.contracts.artifact_projection_mapper` → `artifact_document_from_content` — `teaching_pack/content_orchestrator.py:224` (`_student_projection` round-trips a generated `ArtifactContent` through V2 `ArtifactDocument` and back, so the persisted student projection is answer-free by construction rather than by convention)
- `common.contracts.diagnostic_report` → `DiagnosticReport` — `sub_agents/diagnostician/nodes.py:12`
- `common.contracts.inverse_thinking` → `CreativeFrame`, `InverseThinkingPack` — `inverse_thinking_pipeline.py:8`
- `common.contracts.methodology_registry` → `MethodologyTag`, `methodology_entry_by_tag` — `sub_agents/planner/staged_engine.py:9`, `sub_agents/content_creator/methodology_helpers.py:7`
- `common.contracts.artifact_workflow` → `ArtifactWorkflowState` — `teaching_pack/quality_runtime.py:5`, `sub_agents/reviewer/live_quality_gate.py:7`
- `common.contracts.seam_contracts` → `PlannerHandoff` — `teaching_pack/nodes.py` (within `_planning_blueprint`)

### packages/quality (17 imports across 14 files) — CONFIRMED

Deterministic quality checks used in compliance gate, LLM judge, and middleware.

- `packages.quality.compliance_policy` → `check_doctype`, `external_asset_issues`, `check_artifact_answer_key_leakage`, `html_hard_blocks`, `hard_block_violations` — `teaching_pack/compliance.py:9`, `gates/presentation/html_validator.py:7`, `gates/presentation/answer_key_guard.py:6`
- `packages.quality.layer2_content.pii` → `detect_pii`, `PiiAuditEvent`, `scrub_pii` — `teaching_pack/compliance.py:10`, `inverse_thinking_pipeline.py:18`, `middleware/safety/guardrail.py:4`
- `packages.quality.layer1_schema.component_gate` → `validate_component_minimums` — `gates/content_reviewer.py:15`
- `packages.quality.layer2_content.component_scorer` → `score_component_usage` — `gates/llm_judge.py:9`
- `packages.quality.layer2_content.methodology` → `check_methodology_compliance` — `gates/content_reviewer.py:16`
- `packages.quality.layer2_content.pedagogical` → `check_pedagogical_metrics` — `tests/teaching_pack/test_generate_one_artifact.py:9`
- `packages.quality.layer6_export.export_validator` → `check_export_readiness` — `tests/test_flashcard_export_e2e.py:24`
- `packages.quality.layer2_content.inverse_thinking` → `validate_inverse_thinking_pack` — `inverse_thinking_pipeline.py:17`

### packages/llm_client (4 imports across 3 files) — CONFIRMED

LLM transport layer.

- `packages.llm_client.client` → `ChatMessage`, `LLMClient`, `ChatCompletionMessageParam`, `ChatResponse` — `llm/chat.py:9`, `runtime.py` (TYPE_CHECKING), `tests/llm/test_transport_policy.py:11`
- `packages.llm_client.errors` → `OpenAIError` — `llm/chat.py:10`
- `packages.llm_client.config` → `LLMClientConfig` — `tests/test_llm_config.py:4`

### packages/methodologies (1 import in 1 file) — CONFIRMED

- `packages.methodologies.inverse_thinking` — `inverse_thinking_pipeline.py:9`

### langgraph (framework dependency)

- `langgraph.graph.StateGraph`, `END` — `teaching_pack/graph.py:50-51`
- `langgraph.types.interrupt` — `teaching_pack/nodes.py` (within `_unit_approval` and teacher gate nodes)
- `langgraph.checkpoint.memory.MemorySaver`, `langgraph.checkpoint.sqlite.SqliteSaver`, `langgraph.checkpoint.postgres.PostgresSaver` — referenced in `checkpointer.py:13-16`

### packages/agents (internal, runtime-resolved)

- `packages.agents.llm` → LLM call wrappers (`runtime.py:8`, `runtime.py:61`)
- `packages.agents.config` → All config singletons (loaded throughout)
- `packages.agents.events` → Event bus (`healing/orchestrator.py:6`, `teaching_pack/compliance.py:6`)
- `packages.agents.prompts.compiler` → `CompiledPrompt` (`runtime.py:11` via TYPE_CHECKING)

### agents → gateway (1 import, TEST ONLY — not a production boundary violation)

- `tests/test_flashcard_export_e2e.py:28` — imports `services.gateway.teaching_pack_export_writer`. Production code has **zero** imports from `services/*`.

### agents → renderer (0 Python imports — DISPROVED)

The hypothesis of 9 imports is incorrect. Agents does NOT import from `packages/renderer` via Python imports. The renderer is invoked via:
1. **Subprocess** — `nodes/finalize.py:28` runs `node packages/renderer/dist/agent-renderer.js`
2. **Protocol boundary** — `teaching_pack/ports.py:97` defines `ArtifactRenderer` protocol
3. **Test-only** — `prompts/tests/test_registry.py:25` imports `TemplateModule` from renderer

## Used by

- **`gateway`** — 26 files import agents for graph construction, events, slide deck engine

### services/gateway (production imports confirmed by grep across 26 files)

- `services/gateway/teaching_pack_executor.py:10-11` — `LangGraphRunnableConfig`, `teaching_pack_thread_config` from `packages.agents.teaching_pack.graph`
- `services/gateway/teaching_pack_executor.py:10` — `safe_error_summary` from `packages.agents.llm.error_summary`
- `services/gateway/routers/runs.py:13` — `get_run_events`, `has_terminal_event`, `subscribe`, `unsubscribe` from `packages.agents.events`
- `services/gateway/observability_events.py:3` — `ObservabilityEvent` from `packages.agents.events`
- `services/gateway/teaching_pack_store.py:9` — `ObservabilityEvent` from `packages.agents.events`
- `services/gateway/teaching_pack_completion.py:6` — `ArtifactContentStore` from `packages.agents.teaching_pack.content_orchestrator`
- `services/gateway/routers/teaching_pack_previews.py:17-19` — `ObservabilityEvent`, `features`, slide_deck_engine components from `packages.agents`
- `services/gateway/research_provider_9router.py:8` — `NineRouterFetchRequest`, `NineRouterSearchRequest` from `packages.agents.tools.ninerouter_web`
- `services/gateway/artifact_rewrite_proposal.py:20` — block rewrite LLM from `packages.agents.slide_deck_engine`
- `services/gateway/artifact_workflow_errors.py:6` — `safe_message_summary` from `packages.agents.llm.error_summary`
- `services/gateway/teaching_session/branches.py:67-68` — `DensityBudgetPolicy`, slide deck quality from `packages.agents.slide_deck_engine`
- `services/gateway/routers/teaching_session_live.py:31-36` — block rewrite LLM and teacher memory from `packages.agents`

### tests/ (cross-package integration)

- `tests/e2e/canonical_flow.py` — `build_teaching_pack_graph`
- `tests/integration/test_full_pipeline.py` — `NodeState`
- `tests/test_basestore_ttl.py` — `build_teaching_pack_graph`

### apps/web (indirect, via gateway HTTP API only — no direct imports)

## Data & side effects

### Environment variables consumed

| Variable | Source | Purpose |
|----------|--------|---------|
| `MODEL_STRONG_DEFAULT` | `config/models.py:60` | Tier alias for strong-tier models |
| `MODEL_FAST_DEFAULT` | `config/models.py:59` | Tier alias for fast-tier models |
| `MODEL_<TASK>` | `config/models.py:40-80` | Per-task model overrides (14 slots) |
| `MAX_TOKENS_<AGENT>` | `config/models.py:107-127` | Per-agent max output tokens |
| `NINEROUTER_*` | `config/models.py:130-147` | 9Router web tool config (timeout, search_results, min_sources, fetch limits) |
| `GATE_*` | `config/gate_config.py:12-74` | Quality gate thresholds (judge score, HITL timeout, circuit breaker, etc.) |
| `FEATURE_TOPIC_DECOMPOSITION_V1` | `config/features.py:22` | Topic decomposition feature flag |
| `FEATURE_VOCABULARY_BATCH_V1` | `config/features.py:23` | Vocabulary batch feature flag |
| `FEATURE_COMPONENT_STRATEGIST_V1` | `config/features.py:24` | Component strategist feature flag |
| `FEATURE_SLIDE_DECK_EDITOR_V1` | `config/features.py:25` | Slide deck editor feature flag |
| `FEATURE_SLIDE_DECK_AI_REWRITE_V1` | `config/features.py:26` | Slide deck AI rewrite feature flag |
| `UNIT_FANOUT_CONCURRENCY` | `config/features.py:27` | Parallel artifact generation concurrency |
| `FEATURE_GENERIC_CONTENT_CREATOR_FALLBACK_V1` | `config/features.py:35` | #464: gates the generic `content_creator_node` fallback in `generate_one_artifact.py` -- off by default (default-deny); `generate_one_artifact` raises `UnsupportedArtifactCapabilityError` instead when an artifact type has no registered specialist and no native dispatch branch |
| `REDIS_URL` / `REDIS_HOST` / `REDIS_PORT` / `REDIS_AUTH` | `healing/circuit_breaker.py:221-235` | Circuit breaker state persistence |

### Network calls

- **LLM calls** via `packages/llm_client` — all traffic routes through 9Router (`http://localhost:20128/v1`) or optional LiteLLM proxy
- **Web search/fetch** via `tools/ninerouter_web.py` — 9Router web tool for research
- **Redis** via `healing/redis_breaker_store.py` — circuit breaker state persistence
- **Langfuse** via `observability/langfuse_client.py` — tracing (optional, degrades to no-op)

### File I/O

- **Checkpointer files** — SQLite at `omc_checkpoints.db` (staging) via `checkpointer.py:60`
- **Renderer subprocess** — `nodes/finalize.py:28` shells out to `node packages/renderer/dist/agent-renderer.js`

### In-memory state

- **Event bus** (`events.py:72-73`) — `_event_store` and `_event_subscribers` dicts, per `run_id`. Not persisted; lost on restart. Used for SSE streaming.
- **Feature flag cache** (`config/features.py:30`) — `_FEATURES` global singleton, lazily initialized.
- **Model assignments singleton** (`config/models.py:150`) — `MODELS` created once at import time.

## Notes / discrepancies vs existing docs

### Corrected from prior trace

1. **"agents → renderer: 9 imports"** — **DISPROVED**. Zero Python imports from `packages.renderer` in production code. Renderer is called via subprocess (`nodes/finalize.py:28`) and Protocol boundary (`ports.py:97`). One test-only import in `prompts/tests/test_registry.py:25`.

2. **"agents → gateway: 17 imports"** — **INCORRECT for production**. Exactly 1 import from `services/*` exists, and it's in a test file (`tests/test_flashcard_export_e2e.py:28`). Production code has zero gateway imports. INVARIANT-02 is clean.

3. **"agents → quality: 20 imports"** — Actual count is 17 (14 production + 3 test). Close but not exact.

4. **"agents → contracts: 184 imports"** — Actual count is 157 across 125 files.

### Structural observations

5. **Component-strategist variant** (`TEACHING_PACK_STAGES_WITH_COMPONENT_STRATEGY`) places `teacher_approval` BEFORE `artifact_workflow` — structurally different from the default path, not just a longer sequence.

6. **Legacy `nodes/` directory** still exists (`state.py`, `finalize.py`, `preflight.py`, `pack_scope.py`, `quickstart.py`) but is NOT part of the authoritative teaching-pack pipeline. Remnants of older graph architecture.

7. **`slide_deck_engine/`** is a substantial sub-module (~15 files) for slide deck generation. Not mentioned in AGENTS.md project structure but actively used by the gateway for slide deck editing (preview, block rewrite, scoped edit).

8. **`effectiveness/`** directory contains student effectiveness tracking (`moet_export.py` for MoET data export). An operational module not in AGENTS.md.

### Runtime-wired dependencies (not visible from imports)

- **Content store** resolved at graph build time (`graph.py:59-61`) — `LangGraphArtifactContentStore(store)` or `InMemoryArtifactContentStore()` by default; the gateway can inject a third implementation, `GatewayArtifactDocumentContentStore` (`services/gateway/artifact_document_content_store.py`), which persists through the V2 `ArtifactDocumentStore`/Postgres instead of the LangGraph store (#463).
- **Quality gate** injected via `quality_gate` parameter to `build_teaching_pack_graph()`. Gateway creates `GatewayTeachingPackQualityGate`.
- **Checkpointer** injected externally; agents provides the factory (`checkpointer.py`).
- **Healing strategies** imported statically (`healing/orchestrator.py:8`) but behavior varies by GateConfig.

---
_Traced from source on 2026-07-11. Files examined in depth: `teaching_pack/graph.py`, `teaching_pack/nodes.py`, `teaching_pack/stages.py`, `teaching_pack/ports.py`, `teaching_pack/compliance.py`, `teaching_pack/quality_routing.py`, `teaching_pack/quality_runtime.py`, `config/models.py`, `config/features.py`, `config/gate_config.py`, `config/model_drift.py`, `runtime.py`, `events.py`, `checkpointer.py`, `middleware/base.py`, `middleware/registry.py`, `healing/orchestrator.py`, `healing/circuit_breaker.py`, `healing/strategies/*.py`, `inverse_thinking_pipeline.py`. Grep-verified all 5 Phase 3 hypothesis edges plus llm_client dependency. Confirmed gateway→agents reverse direction across 26 gateway files._
