# ADR-035: Component Strategist Stage

## Status

**Proposed** (2026-07-05) — Add a first-class, closed-loop Component Strategist that chooses pedagogical learning moves and typed renderable components before artifact generation. The strategist runs in provisional and final modes around research so final strategy uses typed research signals. This is a production rebuild of component choice, not a prompt patch on Content Creator. Detail lives in `.scratch/component-strategist/`.

## Context

The teaching-pack runtime already has strong pieces for rich output: `LessonPlan`, `ArtifactContent`, typed `ContentComponent`, renderer dispatcher/templates, `methodology_registry`, teacher memory namespaces, quality gates, artifact fanout, and teacher approval gates. The weak seam is that component choice is still mostly prompt-driven or deterministic-prose-driven:

- the planner emits `learning_plan` as Gagne-event text rather than a structured component strategy;
- the deterministic hierarchical creator can reduce a section to `heading` + `paragraph`, with methodology requirements expressed as prose instead of typed components;
- the LLM creator is constrained by prompts but still owns architecture selection;
- teacher approval sees generated content, not an inspectable pedagogical component plan;
- existing component metadata and question-type metadata are not used as a first-class selector.

The product need is not “more templates”; it is smarter lesson architecture: teacher-trustworthy, explainable, evidence-based component choice that makes packs less repetitive and better adapted to class context.

## Decision

1. **Add two first-class strategy passes around research.** The graph runs `provisional_component_strategy` after `planning_blueprint`, then `post_blueprint_research`, then `finalize_component_strategy`, then teacher blueprint/strategy approval, then `artifact_workflow`. Provisional strategy guides research questions and hypotheses; final strategy uses typed `ResearchSignals` and is the only strategy consumed by Content Creator.
2. **Use one standalone engine with modes, not two selectors.** The external interface is a deep module: `plan_component_strategy(ComponentStrategyRequest) -> ComponentStrategyResult`. `ComponentStrategyRequest.mode` is `provisional` or `final`. The core never receives raw `TeachingPackState`; LangGraph nodes are thin adapters.
3. **Strategy core = learning sequence, not component list.** The canonical plan is a move-centric `learning_sequence`; artifact strategies are projections. The strategist first chooses pedagogical learning moves — e.g. misconception probe, contrast near-confusable concepts, worked example, guided practice, retrieval, transfer, reflection — then attaches exact contract-backed component/exercise types as implementations of each move.
4. **Deterministic selector owns authority.** Hard filters, scoring, diversity/cohesion rules, fallback, and gate decisions are deterministic and inspectable. LLM is optional, cacheable, and constrained to teacher-facing rationale polish or tie-breaks among already-eligible candidates. LLM output can never introduce unsupported component types, bypass hard filters, alter scores, or select architecture.
5. **Hard-filter-first scoring.** A candidate that fails artifact support, renderer capability, contract support, grade/readiness fit, language/compliance, answer-key separation, offline/export requirements, or prerequisite feasibility is ineligible. Scores compare only already-valid candidates.
6. **Pack-level strategy with artifact/export projections.** The strategist plans the whole teaching-pack arc, then projects ordered slots into lesson, worksheet, quiz, recap, and requested exports. Required export formats participate in eligibility; optional export degradation is allowed only with visible warnings.
7. **Closed-loop but evidence-first.** Pedagogy evidence and renderability are the source of truth. Teacher preferences, future outcome signals, engagement, and novelty are bounded soft multipliers only; they never override compliance, renderability, readiness, objective coverage, or pedagogy hard filters.
8. **Content Creator becomes filler/adapter.** It fills selected ordered slots with grounded, age-appropriate content. It may return typed fill failure or request strategy fallback, but it may not silently replace selected components with prose, reorder learning moves, or choose replacement architecture.
9. **One recommended strategy plus up to two meaningful variants.** The default strategy is evidence-balanced. Optional variants such as exam-focused and engagement-focused are produced by explicit scoring profiles through the same scorer and are exposed only when meaningfully distinct and valid.
10. **Teacher approval happens once, after final strategy.** Blueprint approval shows the finalized strategy, variants, key tradeoffs, fallback warnings, and typed feedback controls before content generation. Provisional strategy is internal/research-guiding and is not approved as final architecture.
11. **V1 includes backend + blueprint UX.** The first release must include the two strategy passes, selector, immutable plan/revisions, content-creator integration, gates, observability, and compact blueprint approval panel. It does not include a full component editor, admin YAML authoring UI, student-outcome learning authority, RL, or SHAP.
12. **Feature-flag rollout, not permanent dual architecture.** Existing planless runs stay compatible. New strategy behavior starts behind `FEATURE_COMPONENT_STRATEGIST_V1`; after proving it, planless/prose-only component architecture is deprecated.
13. **Fallback, feedback conflicts, and validation are governed separately.** Strategy fallback and teacher-feedback conflicts follow ADR-037. Slot lineage, move-specific fill validators, rendered-output gates, and release gates follow ADR-038.

## Consequences

- Component choice becomes explainable and testable before artifact generation burns tokens/time.
- Research becomes more targeted because provisional strategy emits typed research questions, while final strategy remains free to contradict provisional hypotheses when research signals justify it.
- Teacher approval improves from “approve generated content” to “approve the finalized teaching strategy”.
- Content generation becomes more modular: strategy selects ordered architecture; Content Creator fills; renderer dispatches; gates verify.
- The graph grows by two strategy passes and the approval UI grows a compact strategy panel.
- The implementation must touch contracts, agent stage wiring, content generation, renderer completeness, quality gates, observability, and frontend UX; this is intentionally not a small patch.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Two-pass Component Strategist around research (chosen) | Explainable before generation; research-informed final architecture; testable; teacher-trustworthy; clean SoC | More contracts/stage/UI work |
| Single component_strategy stage before research | Simple graph insertion | Final strategy lacks typed research signals; can choose bad shapes for factual risk/misconceptions |
| Single component_strategy stage after research | Research-informed final plan | Research is less targeted; teacher sees strategy later; harder to preview architecture early |
| Add more Content Creator prompt rules | Fast | Keeps architecture selection inside an LLM prompt; hard to test; repeats current failure mode |
| Make a free-form specialized LLM sub-agent | Feels smart | Non-deterministic authority; hard to reproduce; can invent unsupported components |
| Hide strategy inside `artifact_workflow` | Less graph/UI change | Teacher cannot approve strategy; harder to debug and regenerate precisely |
| Build a full component editor first | Maximum control | Heavy UX; undermines smart default; not necessary for v1 |

## References

- ADR-002 teaching-pack stage architecture
- ADR-003 run contract and conditional HITL
- ADR-009 quality healing and safety gates
- ADR-019 learning-outcome effectiveness loop
- ADR-020 LangGraph Send artifact fanout
- ADR-025 renderer artifact-kind plugin registry
- ADR-033 specialized module standard
- ADR-037 component strategy fallback and feedback conflicts
- ADR-038 component strategy validators and release gates
- `.scratch/component-strategist/README.md`
