# ADR-053: Content Orchestrator, Artifact Specialists, and Capability Packs

## Status

**Accepted** (2026-07-10) — Replace the universal content-generation path with one Content Orchestrator dispatching deep Artifact Specialist modules, composed with governed subject capabilities and an authoritative component strategy.

## Context

The current content-creator boundary has two useful properties: content generation is centralized behind one seam, and artifact fan-out can isolate failures. However, one universal generation policy cannot provide deep lesson design, assessment correctness, practice progression, synthesis, and slide presentation behavior at the same quality bar.

Creating an autonomous graph agent for every artifact and subject would produce a 5×N or 12×N agent matrix, duplicate orchestration, and weaken pack coherence. The existing `SlideDeckEngine` demonstrates a better pattern: a specialized deep module behind the shared Content Creator boundary.

## Decision

### One Content Orchestrator

`packages/agents` owns a package-level **Content Orchestrator** deep module. It owns:

- Content Brief assembly;
- artifact dependency planning and generation waves;
- specialist and capability registry resolution;
- generation and repair request dispatch;
- bounded parallelism and generation-cycle identity;
- branch result and workflow-status materialization;
- dependency-aware repair requests;
- provenance required by downstream quality and approval.

The teaching-pack graph remains the orchestration authority. Its artifact stage is a thin adapter/router, and a generic `generate_artifact` worker node invokes the Content Orchestrator. The gateway persists jobs and domain objects but does not own pedagogical generation orchestration.

Graph state remains compact; it carries IDs, revisions, routing status, and branch summaries rather than full artifact payloads.

### Five Artifact Specialist families

The Content Orchestrator dispatches to five deep specialist families:

1. **Lesson Design** — `lesson`
2. **Assessment** — `quiz`, `exit_ticket`, and atomic `AnswerSet` generation
3. **Practice** — `worksheet`, `drill`, `flashcard_deck`, and their atomic `AnswerSet`s when applicable
4. **Synthesis** — `recap`, `infographic`, `roadmap`, `reading_passage`
5. **Presentation** — `slide_deck` through `SlideDeckEngine`

`answer_key` is derived from `AnswerSet`, not a separate free-running specialist call.

Each specialist owns its generation policy, typed request/result, governed prompt modules or deterministic engine, parsing, local validation, repair interface, and family-specific scorecard inputs. A specialist is a deep module, not an autonomous tool-using loop or necessarily a LangGraph subgraph.

### Strategy authority with bounded specialist choice

Component Strategy remains authoritative over:

- learning moves and sequence;
- objective coverage;
- required slots and artifact scope;
- methodology and hard constraints;
- export and audience requirements.

Within an approved slot, a specialist may choose among eligible component or exercise variants. It may not silently replace learning moves, remove objectives, change methodology, or change artifact scope. If the approved strategy cannot be filled, the specialist returns a typed fill failure or strategy-change request.

Artifact-wide restructuring requires a new strategy revision and Planning Review. The quality gate is not used as a cleanup mechanism for unconstrained architecture changes.

### Shared Content Brief and dependency references

The orchestrator derives a compact, typed **Content Brief** from the Teaching Brief, lesson blueprint, final component strategy, Research Brief, Class Profile, and approved policy. It carries approved objectives, terminology, vocabulary, examples, misconceptions, style, answer policy, source references, and dependency references.

Specialists receive only the Content Brief and approved dependency artifacts needed for their slot. They do not chat directly with one another and do not receive unbounded full run state.

Default generation waves are:

- Wave 0: `lesson`
- Wave 1: `worksheet`, `quiz`, and `slide_deck` when their declared dependencies are satisfied
- Wave 2: `recap`

Additional artifacts are placed by a typed dependency plan. A slide deck does not wait for worksheet or quiz unless the approved strategy explicitly embeds those activities.

### Four Subject Capability Packs

Specialists compose with four governed **Subject Capability Packs**:

1. Math
2. Science
3. Language and Literacy
4. Humanities and Social Studies, with history, geography, civics, and literature overlays

A Subject Capability Pack supplies subject-specific exercise types, misconceptions, terminology, domain validators, scorecard criteria, prompt modules, curriculum mappings, and contraindications. It does not become a separate autonomous agent.

Language and Literacy distinguishes `target_language` from `instruction_language`. For example, English may be taught with Vietnamese instructions.

Generation and eval policy uses four Grade Bands: K–2, 3–5, 6–8, and 9–12. The exact grade remains available for finer adaptation.

Full-Breadth V1 certifies governed alignment for MOET 2018, CCSS, and NGSS. Generic curriculum mode may use teacher objectives and Bloom/UbD, but it does not claim certified alignment.

### Methodology authority

A teacher may pin a methodology in the Teaching Brief. Otherwise Component Strategy recommends one from the governed methodology registry and exposes a concise rationale in Planning Review. Specialists implement the approved methodology through typed learning moves and components and do not substitute another methodology silently.

### Personalization authority

Personalization inputs have three tiers:

- Teaching Brief and Class Profile are authoritative;
- typed teacher preferences and history are bounded, decayed soft signals;
- student-level evidence is used only in explicit diagnostic mode after privacy controls.

The system does not fine-tune models, mutate pedagogy knowledge, or store raw edit text as hidden memory in V1.

## Consequences

- Artifact families can become genuinely specialized without multiplying graph topologies.
- Subject expertise is composable and governed instead of hidden in ad hoc prompt text.
- Pack coherence is supported by shared typed context and explicit dependencies.
- The existing Content Creator invariant remains intact: the graph owns orchestration and content is generated only through the Content Orchestrator boundary.
- Specialist and capability registries require completeness, contract, and release-evidence gates.

## Considered Options

- **One universal agent with overlays**: rejected because artifact competence remains too shallow.
- **One agent per artifact**: rejected because orchestration and evaluation surface multiply without adding a stable capability model.
- **Agents organized primarily by subject**: rejected because each subject agent would need to reimplement all artifact lifecycles.
- **Autonomous specialist debate**: rejected because it adds latency, weakens determinism, and creates untyped coordination.
- **Specialist-owned component architecture**: rejected because it bypasses the approved pedagogical strategy.

## References

- ADR-020 LangGraph Send Artifact Fan-Out
- ADR-033 Specialized Module Standard
- ADR-035 Component Strategist Stage
- ADR-036 Component Strategy Knowledge and Governance
- ADR-037 Component Strategy Fallback and Feedback Conflicts
- ADR-038 Component Strategy Validators and Release Gates
- ADR-040 Native Slide Deck Artifact and SlideDeckEngine
- ADR-049 Slide Deck Remains Deterministic; Other Artifact Types Flip to Real LLM
