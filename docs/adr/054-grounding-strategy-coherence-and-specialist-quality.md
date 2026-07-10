# ADR-054: Grounding, Strategy, Coherence, and Specialist Quality Authority

## Status

**Accepted** (2026-07-10) — Define how evidence, component strategy, artifact specialists, deterministic validators, quality judges, and healing share authority without silently overriding teachers or one another.

## Context

A full-breadth generator can pass schema validation while still being pedagogically repetitive, factually uncertain, internally inconsistent, inaccessible, or wrong. Generic quality gates are necessary safety infrastructure but are not a sufficient definition of quality for lesson design, assessment, practice, synthesis, and presentation.

Authority must also remain clear. Research owns evidence collection; Component Strategy owns pedagogical architecture; specialists fill approved architecture; quality verifies output; teachers own explicit edits and final approval. Allowing any one of these actors to silently take over another's decisions would make behavior hard to explain and unsafe to repair.

## Decision

### Risk-adaptive grounding

Research Engine is the only search and fetch authority. Artifact Specialists consume curated Research Briefs and do not independently search the web.

Grounding behavior is risk-adaptive:

- low-risk content may use approved deterministic knowledge and teacher sources;
- factual, current, curriculum-sensitive, or high-risk claims require curated evidence;
- rigorous mode requires stronger coverage and source diversity;
- high-risk claims such as dates, numbers, definitions, scientific mechanisms, and policy or curriculum claims fail closed when evidence does not entail the claim;
- medium-risk uncertainty is teacher-visible and cannot be represented as verified;
- creative examples do not require citations unless presented as fact.

`UNCERTAIN` claims do not silently reach student output.

### Teacher Source Collections have declared authority

A Source Collection entry is `required`, `preferred`, or `reference`. Teacher ownership or copyright acknowledgement is required. The Research Engine extracts bounded excerpts and citations; raw documents are not copied into artifacts.

Safety and legal hard blocks always prevail. A material conflict between a required source and verified or certified evidence opens an explicit Planning Review with evidence and options. Neither source silently wins, and disputed claims are not generated before resolution.

Research outage behavior is risk-dependent. Low-risk/basic work may continue with approved internal or teacher sources and visible `grounding_degraded` provenance. High-risk/current/rigorous work blocks affected artifacts and offers retry, source upload, or explicit scope downgrade. Unaffected artifacts may continue to partial review.

### Pack Coherence Review after fan-in

Specialists coordinate through the typed Content Brief and dependency artifacts, not agent-to-agent conversation. After fan-in, Pack Coherence Review checks:

- objective and terminology alignment;
- example and misconception consistency;
- assessment alignment with instruction and practice;
- duplicate or conflicting instructions;
- answer and student/teacher separation;
- dependency and export readiness.

Deterministic checks run first. Targeted model judgment handles criteria that are not reliably deterministic. Failures route to the narrowest safe repair scope.

### Family-specific scorecards and golden scenarios

The six shared quality layers remain authoritative for schema, safety, presentation, human approval, and export readiness. Each specialist family additionally owns deterministic metrics and a targeted rubric. Examples include:

- Lesson Design: objective coverage, instructional sequence, pacing, cognitive load, methodology fidelity;
- Assessment: answer validity, distractor quality, objective coverage, ambiguity, scoring consistency;
- Practice: scaffold progression, retrieval, feedback, difficulty progression, transfer;
- Synthesis: compression fidelity, concept relationships, recall utility, source fidelity;
- Presentation: density, pacing, visual variety, interaction fit, teacher-only separation.

Release evidence uses English and Vietnamese golden teacher scenarios across subject overlays and Grade Bands. LLM judges supplement, but do not replace, deterministic checks.

### Deterministic-first assessment correctness

Supported assessment domains require deterministic validators or solvers before model judgment, including:

- answer cardinality and option uniqueness;
- matching bijection;
- ordering and cloze normalization;
- numerical recomputation where supported;
- Vietnamese four-item true/false scoring;
- answer/question ID integrity.

Items that cannot be machine-verified carry an explicit risk classification, stronger rubric, and teacher-review requirement. They are never labelled deterministically verified.

### Contextual K-12 safety

Safety classification distinguishes legitimate curriculum treatment from harmful facilitation. Grade, subject, curriculum, and audience inform risk policy. Sensitive health, violence, sexual-content, or civics topics may trigger Planning Review and stricter evidence requirements rather than a blanket keyword ban. Exploitation, harmful facilitation, student PII leakage, and other prohibited content remain hard blocks.

### Authority-aware healing

Machine-generated content may be automatically repaired within its budget. Teacher-authored or teacher-confirmed entities are never rewritten silently.

- schema or hard-block violations may reject save or offer a teacher-confirmed patch;
- coherence problems produce impact and repair suggestions;
- block or question rewrite is the default AI repair scope;
- section repair requires impact preview;
- artifact-wide restructuring creates a strategy revision and Planning Review;
- no one-click whole-pack rewrite exists.

### Partial review with fail-closed composite export

When an artifact exhausts bounded healing, passed artifacts remain reviewable. Failed artifacts show safe failure class, provenance, and teacher actions. Required missing or failed artifacts block composite export. An approved artifact may export independently only when its dependencies are current and the selected export supports it.

### Multi-dimensional budgets and outage behavior

Budgets cover latency, tokens, calls, retries, healing attempts, and concurrency, not only USD. Exhaustion transitions to partial review or escalation instead of unbounded loops.

When all approved model routes are unavailable, jobs use bounded retries and cooldown, then enter `provider_unavailable` partial state. The system does not use unapproved or paid providers and does not pass template placeholders off as generated content.

## Consequences

- “Quality” becomes measurable per pedagogical capability, not synonymous with schema pass.
- Evidence uncertainty and source conflicts remain visible and actionable.
- Teacher authority is preserved during healing.
- Partial work is not discarded, while required composite outputs remain fail-closed.
- Test infrastructure must include deterministic domain validators, golden scenarios, and targeted live-model acceptance.

## Considered Options

- **Search inside every specialist**: rejected because evidence policy and caching would fragment.
- **Common quality gate only**: rejected because specialist competence would remain unmeasured.
- **Three-judge correctness authority**: rejected because consensus does not prove answer or factual correctness.
- **Always search everything**: rejected because low-risk latency and prompt volume would rise without proportional value.
- **Automatic repair of teacher edits**: rejected because it violates content authority and trust.
- **Fail the whole run on one artifact**: rejected because artifact-level workflow exists specifically to preserve safe partial progress.

## References

- ADR-006 Research Engine
- ADR-009 Quality, Healing, and Safety Gates
- ADR-013 Prompt, Template, and Rubric Governance
- ADR-029 Healing Escalation to Teacher Review
- ADR-035 Component Strategist Stage
- ADR-037 Component Strategy Fallback and Feedback Conflicts
- ADR-038 Component Strategy Validators and Release Gates
