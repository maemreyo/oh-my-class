---
slug: real-llm-pipeline-wiring
status: awaiting-approval
intent: clear
pending-action: write .omo/plans/real-llm-pipeline-wiring.md
approach: Wire per-artifact real-LLM generation into the active LangGraph content creator path, preserve teacher gates, harden quality/export readiness around existing contracts, then run real 9router E2E scenarios through the HTTP surface.
---

# Draft: real-llm-pipeline-wiring

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->

| C1 | Content creator generates each requested artifact independently instead of one huge JSON array call | active | packages/agents/sub_agents/content_creator/nodes.py:28, packages/agents/sub_agents/content_creator/agent.py:36 |
| C2 | Active graph routing/healing preserves per-artifact failures and does not silently pass placeholders | active | packages/agents/graph.py:189, packages/agents/healing/orchestrator.py:48 |
| C3 | Schema/content/judge gates validate component-based artifacts from real LLM output | active | packages/agents/gates/schema_validator.py:40, packages/agents/gates/content_reviewer.py:20, packages/agents/gates/llm_judge.py:61 |
| C4 | Export readiness/finalize uses the same format requirements and produces standalone HTML only | active | packages/agents/gates/export_readiness.py:17, packages/quality/layer6_export/export_validator.py:54, packages/agents/nodes/finalize.py:53 |
| C5 | Real-LLM E2E harness drives the gateway/approval surface against 9router :20228 and records scenario evidence | active | scripts/test_e2e_real_llm.py, services/gateway/routers/approvals.py:81 |

## Open assumptions (announced defaults)
<!-- Record any default you adopt instead of asking, so the user can veto it at the gate. -->
<!-- assumption | adopted default | rationale | reversible? -->

| Generation unit | Generate one ArtifactContent per LLM call, not one array for all artifacts | Existing single-call output truncates with 4omc reasoning tokens; AGENTS says content creator outputs ArtifactContent and one responsibility per node | yes |
| Where to wire | Keep wiring inside packages/agents content_creator path, not import services/gateway/artifact_workflow.py into packages/agents | Package boundary forbids packages importing services; graph already calls packages/agents/sub_agents/content_creator/agent.py | yes |
| Orchestrator reuse | Reuse the service orchestrator's concepts (plan/waves/per-artifact state), not the service module directly | services/gateway/artifact_workflow.py already proves per-artifact dependency/run state, but direct import would violate package boundaries | yes |
| Export scope before broad tests | HTML first; do not add GIFT/H5P/QTI until HTML full flow is stable | step_11_export_readiness only supports html today, while quality/layer6 has broader format placeholders | yes |
| Test strategy | Tests-after plus real manual QA through HTTP/gateway | Existing breakage is integration/runtime with 4omc; full TDD against a live LLM would be slow and brittle | yes |

## Findings (cited - path:lines)

- Active LangGraph step 08 is `content_creator_graph_node`, not `services/gateway/artifact_workflow.py` (`packages/agents/graph.py:189`).
- `content_creator_graph_node` extracts graph state then calls `content_creator_node` directly (`packages/agents/sub_agents/content_creator/agent.py:36`).
- `content_creator_node` prompts for all requested artifact types and asks for one JSON array in a single `compiled_json_chat` call (`packages/agents/sub_agents/content_creator/nodes.py:40`, `packages/agents/sub_agents/content_creator/nodes.py:91`). This is the truncation point observed in real-LLM testing.
- `services/gateway/artifact_workflow.py` has a stronger per-artifact orchestration design: plan dependencies, run execution waves, validate/heal each artifact independently, and retain passed artifacts (`services/gateway/artifact_workflow.py:86`, `services/gateway/artifact_workflow.py:103`, `services/gateway/artifact_workflow.py:132`). It cannot be imported upward into `packages/agents` without violating package boundaries.
- Schema validation already accepts component-only sections and checks non-empty `content` or `components` (`packages/agents/gates/schema_validator.py:32`, `packages/agents/gates/schema_validator.py:40`).
- Content review currently extracts only `section.content` for fact/age checks; component text may be under-reviewed if real LLM output is component-first (`packages/agents/gates/content_reviewer.py:35`).
- Layer 4 judge is currently heuristic, not real multi-judge; it also extracts only `section.content`, so component-first artifacts can under-score (`packages/agents/gates/llm_judge.py:13`, `packages/agents/gates/llm_judge.py:61`).
- Export readiness in the active graph is HTML-only and separate from the broader `ExportValidator` stub (`packages/agents/gates/export_readiness.py:11`, `packages/quality/layer6_export/export_validator.py:68`).
- Finalize rebuilds the renderer per artifact and only checks external URLs in `section.content`, not nested component payloads (`packages/agents/nodes/finalize.py:18`, `packages/agents/nodes/finalize.py:35`, `packages/agents/nodes/finalize.py:53`).
- Teacher approval endpoints resume the graph through the real LangGraph `Command(resume=...)` surface, so E2E tests should use these endpoints, not direct node calls (`services/gateway/routers/approvals.py:81`).
- Dirty worktree exists from prior real-LLM fixes: `common/contracts/artifact.py`, `packages/agents/sub_agents/content_creator/prompts/system.md`, `packages/agents/sub_agents/researcher/nodes.py`, `scripts/test_e2e_real_llm.py`, `scripts/test_full_flow.py`. Plan must preserve and build on these, not revert them.

## Decisions (with rationale)

- Plan the implementation as a package-local refactor: add per-artifact generation helpers under `packages/agents/sub_agents/content_creator/`, then have `content_creator_node` loop/wave over artifact types and return the same `{"artifacts": [...]}` shape. This fixes the truncation without changing graph topology or importing from `services/`.
- Keep service `ArtifactOrchestrator` as a reference, not a dependency. If shared reuse is later wanted, extract a lower-level abstraction into `common` or `packages`, but do not do that in this stabilization slice.
- Harden gates for component-first content before broad real-LLM tests: shared text extraction for schema/content/judge/export checks must include nested components.
- Treat placeholders as terminal failures for real testing; do not allow fallback placeholders to masquerade as successful generated artifacts.
- Keep real E2E scenarios serial and evidence-heavy because 4omc calls are slow and upstream timeouts are possible.

## Scope IN

- Per-artifact content creator generation in the active `packages/agents` graph path.
- Retry/error metadata per artifact, including retaining successful artifacts when one artifact fails.
- Component-aware text/external-URL extraction for gates and finalize.
- HTML export readiness/finalize stabilization.
- Real 9router :20228 / model 4omc gateway E2E harness and scenario evidence.
- Tests for package-local behavior plus one or more live full-flow manual QA runs after implementation.

## Scope OUT (Must NOT have)

- Must NOT import `services/gateway/*` from `packages/agents/*`.
- Must NOT bypass or auto-approve teacher gates.
- Must NOT broaden export implementation to GIFT/H5P/QTI in this slice.
- Must NOT hide failures with placeholder artifacts in real-flow success criteria.
- Must NOT weaken schema/content gates just to make 4omc output pass.
- Must NOT run more broad scenario tests before the wiring changes are implemented and local checks pass.

## Open questions

None blocking. If you disagree with any adopted default above, veto it before approving the plan.

## Approval gate
status: awaiting-approval
pending action: write the decision-complete todo plan into .omo/plans/real-llm-pipeline-wiring.md
approval needed: approve the approach/defaults above, or veto one specific default before plan writing
<!-- When exploration is exhausted and unknowns are answered, set status: awaiting-approval. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->
