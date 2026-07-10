# oh-my-class Context

## Glossary

### Teaching Content Creator

The unified product capability that lets a teacher create, review, revise, approve, and export teaching content. It includes both the teacher-facing Creator Workspace and the Teaching Content Generation Engine; it is not a separate pipeline beside the teaching-pack lifecycle.

### Creator Workspace

The persistent teacher-facing surface of the Teaching Content Creator. It keeps the Teaching Brief and approved plan, artifact canvas, sources and quality inspector, generation status, scoped revisions, approvals, versions, and exports in one continuing context without exposing internal agent or graph mechanics.

### Teaching Content Generation Engine

The internal capability of the Teaching Content Creator that turns an approved teaching intent into typed, grounded, quality-gated artifacts. It uses the existing teaching-pack stages, specialist agents, deterministic component strategy, renderer, and scoped healing rather than forming a second orchestration system.

### Teaching Pack

The default creation unit of the Teaching Content Creator: a coherent set of teaching artifacts for one lesson or teaching session. Its default recipe is lesson, worksheet, quiz, recap, and slide deck, with context-aware artifact additions. The artifacts share one teaching intent and are reviewed for consistency as a pack.

### Full-Breadth V1

The first releasable Teaching Content Creator, delivered as one production release rather than a partial MVP label. It covers all twelve core artifact surfaces, five Specialist Families, four Subject Capability Packs, English and Vietnamese, structured editing, and every declared export capability at one release quality bar.

### Artifact Quick Create

A narrow creation path for a teacher who needs one artifact rather than a complete Teaching Pack. It remains part of the same creation, quality, revision, approval, and export lifecycle; it is not a separate generator.

### Unit Plan

A multi-session teaching plan whose sessions can each produce a Teaching Pack. Unit planning is an advanced creation scope rather than the default starting point.

### Teaching Brief

The teacher's hybrid expression of teaching intent: a natural-language request plus a small set of structured controls such as grade, subject, language, creation scope, artifact selection, and output needs. Missing or risky assumptions are resolved through conditional clarification before the brief becomes an executable Run Contract.

### Planning Review

A conditional teacher checkpoint over the proposed lesson blueprint and teaching strategy before content generation. It is required when assumptions, risk, fallback, scope, or strategy changes are material, and optional when the plan is high-confidence and remains within the Teaching Brief. It is distinct from final approval of rendered content.

### Content Orchestrator

The single generation boundary that coordinates grounded inputs, artifact dependencies, specialist dispatch, typed output validation, provenance, and pack coherence. It does not author every artifact through one universal prompt and does not replace the teaching-pack stage graph.

### Artifact Specialist

A focused content-generation module behind the Content Orchestrator that owns the generation policy, prompts or deterministic engine, typed output, and artifact-specific validation for one pedagogical capability or artifact family. An Artifact Specialist is not necessarily a separate graph node or autonomous agent.

### Specialist Families

The five pedagogical capability groups used to dispatch content generation: Lesson Design for lessons; Assessment for quizzes, answer keys, and exit tickets; Practice for worksheets, drills, and flashcard decks; Synthesis for recaps, infographics, roadmaps, and reading passages; and Presentation for slide decks.

### Bounded Specialist Choice

The authority granted to an Artifact Specialist inside an approved teaching strategy. The specialist may choose valid component or exercise variants within a strategy slot, but may not silently change learning moves, objective coverage, required constraints, or artifact scope. A material mismatch is returned as a typed fill failure or strategy-change request.

### Personalization Authority

The precedence used when adapting generated content. The current Teaching Brief and Class Profile are authoritative inputs; teacher preferences and history are bounded soft signals; student-level evidence is used only in an explicit diagnostic creation mode after privacy controls are applied.

### Grounding Policy

The risk-adaptive rule for factual evidence used by generation. Low-risk content may use approved deterministic knowledge and teacher-provided sources; factual, current, curriculum-sensitive, or rigorous work requires curated research evidence. Artifact Specialists consume a Research Brief and do not perform independent search.

### Decision Provenance

The teacher-visible explanation of how generated content was produced: approved inputs, source evidence, concise strategy rationale, specialist identity, quality scorecards, fallbacks, warnings, and version lineage. Decision Provenance excludes hidden reasoning, raw prompts, provider traces, and internal graph state.

### Language Version

An immutable artifact content version in one canonical language. Translation creates a derived Language Version with source lineage and its own quality and approval status. Bilingual output exists only when explicitly requested and supported by the artifact contract.

### Content Brief

The compact, typed generation context shared by Artifact Specialists for one Teaching Pack. It carries approved objectives, vocabulary, examples, misconceptions, style, answer policy, source references, and dependency references. It is derived from the Teaching Brief, blueprint, component strategy, and Research Brief.

### Pack Coherence Review

The post-generation review that checks the assembled Teaching Pack for cross-artifact alignment and routes scoped repair. It combines deterministic checks with targeted model judgment and does not permit Artifact Specialists to coordinate through untyped agent-to-agent conversation.

### Subject Capability Pack

A composable, typed subject overlay used by Artifact Specialists. It supplies subject-specific exercise types, misconceptions, terminology, domain validators, rubric criteria, prompt modules, and curriculum mappings without creating a separate autonomous agent for every subject and artifact combination.

### Target Language

The language being taught in a Language and Literacy context. It is distinct from Instruction Language, which is the language used to explain directions and render surrounding teaching content.

### Grade Band

One of four developmental ranges used by generation and quality policy: K–2, 3–5, 6–8, or 9–12. A learner's exact grade belongs to one Grade Band but remains available for finer adaptation.

### Certified Curriculum Alignment

A product claim that generated content has been checked against a governed curriculum mapping and its release evidence. Full-Breadth V1 certifies MOET 2018, CCSS, and NGSS alignment; generic content does not imply certification.

### Visual Source Suggestion

A teacher-facing reference to a potentially useful external visual discovered during research. It is never embedded or packaged automatically. The teacher remains responsible for reviewing its license, downloading it, and adding it to the Media Library before it can become an offline-safe artifact asset.

### Media Asset Version

An immutable, teacher-owned version of an uploaded or locally generated media asset, including its source or license note, checksum, and accessibility status. Artifact content refers to a specific Media Asset Version rather than a mutable shared file.

### Methodology Authority

The precedence for selecting a teaching methodology. A teacher may pin a methodology in the Teaching Brief; otherwise the Component Strategist recommends one from the governed methodology registry and exposes its rationale in Planning Review. Artifact Specialists implement the approved methodology and do not replace it silently.

### Structured Artifact Edit

A teacher-authored or teacher-confirmed AI-assisted change to a typed section, component, question, slide, or block. Structured Artifact Edits never modify raw HTML, create an immutable content version, and trigger quality checks appropriate to the changed scope.

### Content Document

The canonical typed content model for an artifact version. It is composed of discriminated, contract-backed sections and blocks rather than arbitrary dictionaries or authored HTML.

### ArtifactDocument

The common envelope for a versioned teaching artifact. It carries shared identity, audience, language, source, dependency, authority, and lifecycle metadata around a discriminated typed payload such as a BlockDocument, AssessmentDocument, or SlideDeckData.

### Content Entity ID

A stable identity carried by every editable document, section, block, question, option, pair, and asset reference. Identity follows the semantic entity across compatible revisions and supports scoped editing, lineage, dependencies, and review.

### Dependency-Aware Invalidation

The lifecycle response to a semantic artifact change. Existing versions remain immutable, while dependent artifacts, rendered snapshots, and exports are marked stale according to the artifact dependency graph. Regeneration and reapproval are scoped to impacted content and are never performed silently.

### Artifact Approval

The run owner's or explicitly delegated review decision over one current artifact version. A composite Teaching Pack is approvable only when its required artifact versions and dependencies are current and approved. Full-Breadth V1 never auto-approves final content.

### Teaching Recipe

A versioned, reusable set of Teaching Brief defaults and creation preferences. It may define artifact scope, methodology, style, subject, curriculum, quality, and export preferences, but it never contains copied generated student content or approved answers.

### Forked Pack

A new Teaching Pack created with explicit lineage to an existing pack. It has a new Teaching Brief, Run Contract, versions, quality results, and approvals; the source pack remains unchanged.

### Source Collection

A teacher-provided set of documents or references whose authority is declared as required, preferred, or reference. Source Collections inform grounding but do not silently override safety, verified evidence, or certified curriculum policy.

### Source Conflict

A material disagreement between a required teacher source and governed evidence or curriculum. Safety and legal hard blocks prevail; other Source Conflicts require an explicit teacher decision before disputed claims are generated.

### AnswerSet

A separate teacher-only, versioned set of answers and explanations linked to student questions by Content Entity ID. Student artifact content never carries AnswerSet data, including in hidden fields or DOM. An answer-key artifact is a teacher-facing projection of an AnswerSet.

### Content Variant

A typed adaptation of an artifact version for a defined learner need or use mode, such as support, challenge, language scaffold, or accessibility adaptation. A Content Variant has source lineage and its own quality and approval state.

### Export Capability Matrix

The declared truth of which artifact and question capabilities each export format supports, degrades, or rejects. Full-Breadth V1 requires real behavior and release evidence for every supported entry; unsupported combinations fail explicitly rather than converting best-effort.

### Cancelled Draft

A Teaching Pack Run that has stopped future work while preserving its durable, unapproved results. Its artifacts remain viewable and forkable, but it cannot produce a composite approved export.

### Teaching Pack Projection

A composite rendered or exported view assembled from the artifacts in a Teaching Pack. It is not independently authored by an Artifact Specialist and must preserve the exact approved artifact versions it contains.

### slide_deck

A core teaching-pack artifact representing a classroom presentation deck. A `slide_deck` is generated, reviewed, quality-gated, regenerated, and exported through the same artifact lifecycle as lessons, worksheets, quizzes, drills, recaps, flashcards, roadmaps, and answer keys.

### SlideDeckData

The canonical typed domain model for a slide deck. It describes deck metadata, slides, blocks, interactions, teacher-only facilitation data, source references, accessibility metadata, media policy metadata, and surface/export readiness. It is the source shape used by generation, rendering, quality gates, and export adapters.

### SlideDeckEngine

The deterministic orchestration module that produces `SlideDeckData` behind the Content Creator seam. It may call LLM providers through schema-bound ports, but layout selection, interaction selection, density policy, accessibility validation, healing, source references, and teacher-only safety are enforced by typed engine phases and registries.

### Slide surface

A projection of one `SlideDeckData` for a specific audience or use mode. The approved surfaces are student presentation HTML, teacher guide/preview HTML, and print HTML.

### Slide registry

A typed extension seam for slide layouts, slide blocks, or slide interactions. Registry entries declare their schema, supported surfaces, density budget, accessibility requirements, print behavior, teacher-only behavior, and fallback behavior.

### Teacher-only slide data

Facilitation content intended for teachers only: speaker notes, pacing cues, misconceptions, explanations, answer guidance, and rubrics. Teacher-only slide data must not appear in student-facing DOM, hidden JSON, data attributes, or export surfaces.

### DeckSourceContext

The normalized source context used to generate a slide deck. It is assembled from lesson blueprint, research brief, teacher constraints, and approved dependency artifacts. Deck pages and blocks may reference this context through source references.
