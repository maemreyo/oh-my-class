# [MOD-10] Build Standards-alignment module on AgentRuntime + Module Standard

Status: TODO
Labels: module-standard, agents, quality, standards-alignment
ADR: 033
Depends on: MOD-01, MOD-02

## Context

Build the Standards-alignment module per `docs/rfc/standards-alignment-module.md` as a
Specialized Module conforming to the ADR-033 6-point standard. It maps a run's learning
objectives to a curriculum framework via a pluggable provider registry (deterministic first,
LLM-assist for fuzzy) and emits a coverage-report artifact (objectives × standards + gaps).
Seed frameworks: US CCSS and Vietnam MOET. It builds on the existing alignment middleware +
curriculum skills; fail-closed so it never claims unsubstantiated alignment.

## Scope

- [ ] Framework provider registry (explicit, no auto-scan): `StandardsFrameworkProvider`
      Protocol + registry seeded with `ccss` and `moet`, sourcing standards catalogs from the
      curriculum skill files already mapped in `packages/agents/skills/registry.py`
      (`ccss_math`, `ccss_ela`, `vn_ministry_2018`). Each provider declares `framework_version`.
- [ ] Scaffold agent via `make new-module KIND=agent NAME=standards_alignment`;
      `AGENT_CAPABILITIES["standards_alignment"]` binds read + curriculum skill loader only;
      no `write_file`/`task` (`packages/agents/tools/capabilities.py:48-58`).
- [ ] Contract (point 1): new `coverage_report` `artifact_type` on `ArtifactContent`
      (`common/contracts/artifact.py:53`) — a **breaking** enum change ⇒ `schema_version` bump +
      boundary adapter + golden fixture per MOD-04. Sections carry objectives × standards
      matrix + gaps + per-mapping evidence/confidence. Preserve Pydantic↔Zod parity.
- [ ] Renderer plugin `coverage_report` at `packages/renderer/src/plugins/coverage-report.ts`
      (mirror `packages/renderer/src/plugins/answer-key.ts:1-59`), registered in the plugin
      list (`packages/renderer/src/core/registry.ts:43-47`).
- [ ] Runtime: deterministic pass first; only fuzzy/unmatched objectives go to LLM-assist via
      `AgentRuntimeConfig(agent="standards_alignment", …, model="4omc")`; no direct transport.
      Every claimed alignment carries evidence + source (`deterministic` | `llm_assisted`).
- [ ] Observability (point 4) tagged with framework key + version; fail-closed (point 5):
      unknown framework refused; uncorroborated LLM alignment emitted as candidate/gap, never
      confirmed. Run under MOD-05 fault boundary.
- [ ] Manifest/version (point 6): both the agent module and the `coverage_report` renderer
      plugin registered in the MOD-03 unified index.
- [ ] Feed the deterministic result into `CurriculumAlignmentMiddleware` /
      `LearningObjectiveAlignmentMiddleware`
      (`packages/agents/middleware/quality/{curriculum_alignment,learning_objective_alignment}.py`)
      to upgrade their heuristic warnings to grounded checks.
- [ ] Tests (point 3): contract, guard (explicit registry, no auto-discovery), live-path
      (deterministic matrix + gaps), real-LLM, safety (unknown framework refused; uncorroborated
      LLM alignment is a candidate).

## Acceptance

- All acceptance tests in `docs/rfc/standards-alignment-module.md` pass.
- MOD-01 conformance passes; MOD-03 shows both the module and the `coverage_report` plugin
  registered + contract + tests + reachable.
- Real-LLM test (9Router `:20228`, model `4omc`) covers one CCSS and one MOET lesson; report
  renders standalone HTML; every confirmed alignment has deterministic evidence.
- MOD-04 golden fixture at the pre-bump `schema_version` still validates via the boundary
  adapter.
- Safety test: unknown framework refused; uncorroborated LLM alignment appears as candidate/gap.

## References

- RFC: `docs/rfc/standards-alignment-module.md`
- `packages/agents/skills/registry.py` (`SKILL_MAP`)
- `packages/agents/middleware/quality/{curriculum_alignment.py:8-35,learning_objective_alignment.py:8-30}`
- `common/contracts/artifact.py:53`
- `packages/renderer/src/plugins/answer-key.ts:1-59`, `packages/renderer/src/core/registry.ts:43-47`
- MOD-01, MOD-02, MOD-04 (breaking-change path), MOD-05

## Implementation notes

- The `coverage_report` enum member is the one deliberately breaking change in this set —
  exercise the full MOD-04 breaking-change path (bump + adapter + golden fixture) as the
  reference example for that policy.
- Deterministic-first is load-bearing for fail-closed: the LLM never confirms an alignment
  alone. Keep the provider catalogs the single source of truth, sourced from the curriculum
  skill files, not duplicated.
