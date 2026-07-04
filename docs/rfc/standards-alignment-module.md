# RFC: Standards-alignment module (framework-pluggable coverage reporting)

Status: Proposed
Owner: agents + quality
Depends on: ADR-033 Specialized Module Standard, Issue #26 `AgentRuntime`, existing alignment middleware + curriculum skills

## Context

Teachers and administrators need to know which curriculum standards an artifact set covers and
where the gaps are — and the claim must be trustworthy. The Standards-alignment module maps a
run's learning objectives to a curriculum framework's standards and emits a **coverage-report
artifact** (objectives × standards, plus gaps). It is a Specialized Module under ADR-033,
built on `AgentRuntime` (`packages/agents/runtime.py:34-49`) and the existing alignment
seams:

- `CurriculumAlignmentMiddleware` (`packages/agents/middleware/quality/curriculum_alignment.py:8-35`)
  and `LearningObjectiveAlignmentMiddleware`
  (`packages/agents/middleware/quality/learning_objective_alignment.py:8-30`) — both are
  today heuristic/warn-only; this module supplies the deterministic mapping they lack.
- Curriculum skill files + explicit registry: `packages/agents/skills/registry.py`
  (`SKILL_MAP`) already maps framework keys to skill files, including `ccss_math`, `ccss_ela`,
  `vn_ministry_2018`, `hsa_exam_prep`, `bloom_taxonomy`. Framework data therefore already has
  an explicit-registration home to extend.

Design stance: **deterministic first, LLM-assist second**. Where the run already carries
structured curriculum data (e.g. `lesson_plan.curriculum_standard`, learning objectives), the
mapping is deterministic. LLM-assist (via `AgentRuntime`) is used only for fuzzy cases and is
never allowed to *assert* an alignment the deterministic layer cannot corroborate — fail-closed
per ADR-033 §Decision.5, so the module never claims unsubstantiated alignment.

Seed frameworks for v1: **US Common Core (CCSS)** and **Vietnam MOET (vn_ministry_2018)** —
both already present in `SKILL_MAP`.

## Interface / Contract changes

- **Framework provider registry** (new, explicit — no auto-scan, ADR-033 §Decision.3): a
  `StandardsFrameworkProvider` Protocol + a registry mapping framework key → provider,
  seeded with `ccss` and `moet`. Each provider exposes a deterministic `map_objectives(...)`
  over its standards catalog (sourced from the curriculum skill files in
  `packages/agents/skills/{ccss_math,ccss_ela,vn_ministry_2018}/SKILL.md`) and declares its
  `framework_version`.
- **Coverage-report artifact**: a new `artifact_type` on `ArtifactContent`
  (`common/contracts/artifact.py:53`) — e.g. `"coverage_report"` — whose `sections` carry the
  objectives × standards matrix + a gaps list + per-mapping evidence/confidence. Adding a
  Literal member is a breaking change to the enum ⇒ bump `schema_version` + add a boundary
  adapter + golden fixture per MOD-04 / ADR-033 §Decision.4.
- A matching **renderer plugin** `coverage_report` under
  `packages/renderer/src/plugins/coverage-report.ts` (mirror
  `packages/renderer/src/plugins/answer-key.ts:1-59`; Zod schema + `sanitizerPolicy` +
  `templatePath`) registered in the plugin list (`packages/renderer/src/core/registry.ts:43-47`)
  so the report renders to standalone HTML and is exportable.

## Runtime design (AgentRuntime + Module Standard)

- **Family**: agent module (LLM-assist) + framework provider registry. Registered in
  `AGENT_CAPABILITIES` under `standards_alignment`, binding read + the curriculum skill loader
  only; no `write_file`, no `task` (mirror
  `packages/agents/tools/capabilities.py:35-39, 48-58`).
- Deterministic pass first: each registered provider maps objectives to standards from its
  catalog. Only unmatched/fuzzy objectives go to the LLM-assist pass via
  `AgentRuntimeConfig(agent="standards_alignment", run_id, step, step_label, model="4omc")`
  and `runtime.complete_compiled_json_with_retries`. The module must not call LiteLLM/OpenAI
  directly.
- **Evidence discipline**: every claimed alignment carries an evidence pointer (the objective
  text + the matched standard code + source: `deterministic` or `llm_assisted`). An
  `llm_assisted` mapping with no deterministic corroboration is recorded as a *candidate*, not
  a *confirmed* alignment.
- **Observability** (MOD-01 point 4): emit `step_started` / `step_completed` / `step_failed`
  (`packages/agents/events.py:71-73`), tagged with framework key + version.
- **Fail-closed** (MOD-01 point 5, MOD-05): if a requested framework has no registered
  provider, the module refuses (does not guess). If the LLM proposes an alignment the
  deterministic catalog cannot corroborate, it is emitted as a gap/candidate, never as
  confirmed coverage. Runs under the MOD-05 fault boundary. The module never overstates
  coverage.
- Build on, not replace, the existing middleware: `CurriculumAlignmentMiddleware` /
  `LearningObjectiveAlignmentMiddleware` can consume this module's deterministic result to turn
  their current heuristic warnings into grounded checks.

## Acceptance

- **Contract test**: the coverage-report validates as `ArtifactContent` with
  `artifact_type="coverage_report"`, an objectives × standards matrix, and a gaps list;
  Pydantic↔Zod parity holds after the `schema_version` bump (`make check-schemas`); a golden
  fixture at the prior schema version still validates via the boundary adapter (MOD-04).
- **Guard test**: the module imports no direct LLM transport, binds only declared
  capabilities, and the framework registry is explicit (a test greps the registry for the
  seeded `ccss` / `moet` providers — no auto-discovery).
- **Live-path test**: given a run with objectives and `curriculum_standard`, the deterministic
  pass produces a coverage matrix with gaps, with no LLM call required for exact matches.
- **Real-LLM test**: through 9Router `:20228`, model `4omc`, run standards alignment for one
  CCSS lesson and one Vietnam MOET lesson; assert the report renders to standalone HTML and
  every confirmed alignment carries deterministic evidence.
- **Safety test (fail-closed)**: (a) an unknown framework key is refused, not guessed;
  (b) an LLM-proposed alignment with no catalog corroboration appears as a candidate/gap, never
  as confirmed coverage.
- **Standard conformance**: passes the MOD-01 conformance test; the module + the
  `coverage_report` renderer plugin both appear in the MOD-03 unified manifest with version
  entries.
