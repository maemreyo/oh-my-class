# RFC: Differentiation module for tiered artifact variants

Status: Proposed
Owner: agents + quality
Depends on: ADR-033 Specialized Module Standard, Issue #26 `AgentRuntime`, ADR-018 runtime parity, existing `ArtifactContent`

## Context

Teachers need one approved artifact to reach a mixed-ability classroom. The Differentiation
module generates tiered *variants* of an already-approved `ArtifactContent`
(`common/contracts/artifact.py:46-110`) so the same lesson meets students where they are. It
is a Specialized Module under ADR-033: it builds on `AgentRuntime`
(`packages/agents/runtime.py:34-49`) via the existing `content_creator` capabilities
(`packages/agents/tools/capabilities.py:35-39`) rather than a bespoke harness, and it satisfies
the 6-point Module Standard.

Scope for v1 axes:

- **Grade-level tiers**: below / at / above the target grade band (`class_info.grade` +
  subject, as used by the accessibility RFC's reading-level logic in
  `docs/rfc/accessibility-agent.md`).
- **ELL / language-support**: a language-scaffolded variant (glossing, sentence frames,
  simplified syntax) — first-class in v1.
- **IEP / individualized accommodations**: explicitly **deferred** (out of scope for v1; the
  contract leaves room but the module does not generate them).

Each variant is a full `ArtifactContent` that independently passes compliance + quality gates,
renders to standalone HTML, and is exportable — surfaced at the teacher gate as sibling
variants of the source artifact.

## Interface / Contract changes

Reuse `ArtifactContent`; do not create a parallel variant model. Add differentiation
provenance fields (additive, non-breaking per ADR-033 §Decision.4 / MOD-04):

- `variant_of_artifact_id`: optional source artifact reference for a generated variant.
- `differentiation_tier`: `Literal["below", "at", "above"]` for grade tiers.
- `differentiation_support`: optional `Literal["ell"]` (v1) — extensible, `iep` reserved but
  not emitted.
- `differentiation_notes`: teacher-visible rationale for the adaptation.

The existing `accessibility.reading_level` / `accessibility.language`
(`common/contracts/artifact.py:68`) remain the student-facing indicators; the new fields
describe *why/how* this is a variant. All additive ⇒ no `schema_version` bump; a golden fixture
per tier is added under MOD-04.

## Runtime design (AgentRuntime + Module Standard)

- **Family**: agent module. Registered in `AGENT_CAPABILITIES` under `differentiation` (or
  reuse `content_creator` capabilities if generation stays inside that agent — decide at build
  time in MOD-09), binding only read + generation capabilities; no `write_file`, no `task`
  (mirror `packages/agents/tools/capabilities.py:35-39, 48-58`).
- Constructs `AgentRuntimeConfig(agent="differentiation", run_id, step, step_label,
  model="4omc")` and generates each variant with one LLM call per (tier × support) via
  `runtime.complete_compiled_json_with_retries`, exactly like
  `packages/agents/sub_agents/content_creator/nodes.py:72-113`. It must not call
  LiteLLM/OpenAI directly.
- Input is the approved source `ArtifactContent` + `class_info` + a differentiation policy
  (which tiers/supports to generate). Output is a list of sibling `ArtifactContent` variants
  flowing through state; the module never writes rendered HTML or files.
- **Gates per variant**: each generated variant runs through the same compliance
  (`packages/agents/teaching_pack/compliance.py`) and quality path as any artifact, including
  `readability_level` and `learning_objective_alignment` middleware
  (`packages/agents/middleware/quality/readability_level.py`,
  `.../learning_objective_alignment.py`). A variant that fails compliance or quality is
  dropped, not surfaced.
- **Observability** (MOD-01 point 4): emit `step_started` / `step_completed` / `step_failed`
  per variant (`packages/agents/events.py:71-73`); attribute cost via `AgentRuntime` tags.
- **Fail-closed** (MOD-01 point 5, MOD-05): on a readability breach (variant reads *above*
  target for a below-tier) or any safety/compliance breach, the variant is discarded and the
  failure is recorded — never surfaced as a passing variant. If the source artifact is not
  approved, the module refuses to run. Runs under the MOD-05 fault boundary (per-variant
  timeout + fail-closed; a single variant failure is a dependency-skip, not a run crash).
- **Rendering**: variants render through the existing renderer plugin for their
  `artifact_type` (`packages/renderer/src/core/registry.ts`); no new renderer plugin required
  because a variant is a normal `ArtifactContent`.

## Acceptance

- **Contract test**: a generated variant validates as `ArtifactContent` with
  `variant_of_artifact_id`, `differentiation_tier`, and (for ELL) `differentiation_support`
  set; additive fields pass Pydantic↔Zod parity (`make check-schemas`).
- **Guard test**: the module imports no direct LLM transport and binds only declared
  capabilities (mirror `docs/rfc/researcher-001-upgrade.md` acceptance).
- **Live-path test**: generates below/at/above + ELL variants from one approved artifact and
  asserts each is a distinct, valid `ArtifactContent`.
- **Real-LLM test**: through 9Router `:20228`, model `4omc`, produce a below-grade and an ELL
  variant of a real approved artifact; assert each passes compliance + quality + renders to
  standalone HTML with no external assets.
- **Safety test (fail-closed)**: a below-tier variant whose estimated reading level exceeds the
  target band is discarded (not surfaced) and the drop is recorded as `step_failed`.
- **Standard conformance**: the module passes the MOD-01 conformance test and appears in the
  MOD-03 unified manifest with a version entry.
