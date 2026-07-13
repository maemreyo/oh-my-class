# Teaching Content Factory to Pedagogical Compiler Design

## Scope

This increment starts from commit `e3198d44ed240596b01e24322a589617ea2f799b`. It fixes the constructed-response `AnswerSet` regression and completes a verification/closure gate for the previously implemented batch #465, #471, #464, #466, #467, #468, #472, and #469. It also delivers production-connected increments for the dependency-safe next issues #470, #473, and #489 through #496; those ten issues remain open until their issue-specific real-path, calibration, parity, persistence, and certification criteria are satisfied.

## Architecture

The existing typed Content Orchestrator remains the production boundary. A new `pedagogical_compiler` contract package introduces deterministic stages:

`TeachingIntent -> ObjectiveGraph -> PedagogicalProgramIR -> SemanticContentIR -> Optimizer/DomainTools -> MultiPassSynthesis -> ArtifactCompiler`

`packages/agents/teaching_pack/pedagogical_compiler_runtime.py` is the sole adapter from `OrchestratorRequest` into those contracts. Existing specialists remain renderer-compatible, but every generated artifact receives compiler hashes, objective/program/semantic lineage, synthesis receipts, tool receipts, and a complete entity projection map before schema validation and persistence.

The Content Quality Benchmark is an independent evaluation plane. Critical lanes are non-compensatory. The effectiveness plane aggregates only exact tenant/document/item/answer versions, excludes opted-out observations, withholds small cohorts, and emits review proposals rather than mutating generation policy.

## Answer semantics

A `question_card.answer` matching an option ID derives `correct_option_ids`. Any other non-empty answer derives `accepted_answers`. Verification validates the appropriate shape rather than forcing all assessment items through selected-response semantics.

## Failure behavior

Material TeachingIntent ambiguity blocks compilation. Objective and semantic graphs reject dangling references and cycles. The optimizer cannot select a hard-failing candidate. Unsupported/failed domain tools cannot create verified evidence. Synthesis preserves valid unrelated entities during scoped repair. Artifact compilation fails on unaccounted semantic loss. Benchmark critical failures block release regardless of aggregate score.

## Verification

The installer runs the original specialist/runtime gates, the constructed-response regression, benchmark/effectiveness simulations, all compiler contract/runtime tests, and architecture truth checks. It closes only the previous eight issues after all commands pass in the same run and every declared blocker is closed. For #470, #473, and #489-#496 it posts an idempotent progress ledger that names both the implemented slice and the remaining Definition-of-Done gaps; it never closes those ten issues.
