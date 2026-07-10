# ADR-051: Teaching Content Creator Product and Lifecycle

## Status

**Accepted** (2026-07-10) — Define Teaching Content Creator as one product capability over the authoritative teaching-pack lifecycle, not as a second generator or orchestration system.

## Context

The repository already contains most of the technical lifecycle required to generate teaching content: a persisted `RunContract`, planning and research stages, component strategy, artifact-level fan-out, quality gates, rendered snapshots, teacher approval, versions, exports, and live slide delivery. The missing product boundary is a coherent teacher experience and a generation architecture whose artifact capabilities are genuinely specialized.

Treating “Teaching Content Creator” as a new service would duplicate the teaching-pack state machine, persistence, gates, and quality authority. Treating it only as an internal `content_creator` agent improvement would leave teachers without an end-to-end creation, revision, and approval experience.

## Decision

### One capability with two surfaces

Teaching Content Creator is one capability composed of:

- **Creator Workspace**: the persistent teacher-facing experience for briefing, planning review, generation progress, rendered review, structured editing, approval, versions, and export.
- **Teaching Content Generation Engine**: the internal capability that turns an approved teaching intent into typed, grounded, quality-gated artifact versions through the existing teaching-pack runtime.

The Generation Engine remains inside the authoritative teaching-pack stage graph. The gateway remains the HTTP, persistence, and job composition boundary. No parallel `/creator` orchestration service or second graph is introduced.

### Pack-first creation model

The default creation unit is one **Teaching Pack** for one lesson or teaching session. Its default recipe is:

1. `lesson`
2. `worksheet`
3. `quiz`
4. `recap`
5. `slide_deck`

The Creator exposes the full artifact catalog through context-aware recommendations. Teachers may add or remove artifacts before generation, subject to dependency and export capability rules.

**Artifact Quick Create** is a narrower scope of the same lifecycle, not a separate generator. **Unit Plan** remains the advanced multi-session mode whose sessions can each produce a Teaching Pack.

### Hybrid Teaching Brief

Creation begins with a **Teaching Brief** containing:

- one natural-language teaching request;
- structured controls for grade, subject, target and instruction language, curriculum, class context, artifact scope, methodology/style preferences, research rigor, and output needs;
- bounded freeform guidance for must/include/avoid constraints.

The system resolves the Teaching Brief into an append-only Run Contract. Structured policy precedence is:

1. safety, privacy, certified curriculum, legal, branding, and export hard policy;
2. explicit Teaching Brief choices;
3. approved Teaching Recipe and Class Profile;
4. bounded learned teacher preferences;
5. system defaults.

Every override is visible in the resolved contract. Teachers cannot edit system prompts or bypass schema, safety, curriculum, or quality constraints.

### Conditional Planning Review

Planning Review covers the proposed lesson blueprint and teaching strategy before content generation. It is required by versioned materiality rules, including:

- inferred topic, language, or curriculum;
- required-source conflict;
- sensitive or high-risk content;
- strategy fallback or profile switch;
- objective, artifact scope, or export change;
- unsupported or degraded capability;
- rigorous research mode;
- unit decomposition;
- organization policy override;
- confidence below the governed threshold.

A teacher may choose “always review.” A teacher may not suppress mandatory materiality events. High-confidence plans within the Teaching Brief may continue automatically.

### Human approval remains mandatory for final content

Final approval applies to current rendered artifact versions. Full-Breadth V1 does not auto-approve final content. The run owner is the default approval authority; an organization may grant explicit, audited delegation. System administrators have operational recovery authority only.

Approval is artifact-level, with bulk “approve all current” support. A composite pack is current and approved only when its required artifact versions and impacted dependencies are current and approved.

### Existing API domain remains authoritative

Backend resources remain under `/teaching-packs`. Additive resources may expose briefs, plans, artifact versions, variants, source collections, approvals, and exports. The product UI may use a Creator route, but “Creator” is not a new backend bounded context.

General DOCX/PDF/PPTX/H5P reverse import is outside V1. Uploaded documents are Source Collections, not automatically editable artifacts. Structured GIFT question-bank import may be added only as an explicit assessment capability.

## Consequences

- Product work and agent work share one lifecycle and one set of contracts.
- Existing teaching-pack persistence, gates, quality, and export infrastructure are deepened rather than duplicated.
- Teachers get a fast default without losing control over material decisions.
- Final content remains human-approved even when planning review is skipped.
- Full breadth is discoverable through recommendations rather than generated wastefully on every run.

## Considered Options

- **Internal agent improvement only**: rejected because it does not create a usable teacher lifecycle.
- **Independent Creator service or graph**: rejected because it duplicates domain authority and persistence.
- **Artifact-first product**: rejected because cross-artifact coherence and the current runtime are pack-oriented.
- **Prompt-only or form-only input**: rejected because one is ambiguous and the other creates unnecessary setup friction.
- **Always approve the plan**: rejected because it adds review fatigue to unambiguous work.
- **Final fast-lane approval**: deferred until post-V1 trust and outcome evidence exist.

## References

- ADR-002 Teaching Pack Stage Architecture
- ADR-003 RunContract and Conditional Human-in-the-Loop
- ADR-026 Fast-Lane Teacher Gate and INVARIANT-06
- ADR-028 Full REST Operability for Teaching-Pack Runs
- ADR-048 Planner Blueprint Generation Remains Deterministic-by-Design
