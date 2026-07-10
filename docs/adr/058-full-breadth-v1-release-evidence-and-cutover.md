# ADR-058: Full-Breadth V1 Release, Evidence, and Big-Bang Cutover

## Status

**Accepted** (2026-07-10) — Define V1 as one full-breadth production release with no public partial V1, require capability-covering evidence through real surfaces, and cut over in one deployment because the product has no production users.

## Context

The chosen V1 scope is intentionally broad. Calling a narrow vertical slice “V1” and moving the remaining artifacts, subjects, languages, editor coverage, or exports to later releases would not match the product decision. Conversely, requiring every mathematically possible permutation would create an enormous test matrix containing meaningless artifact/export combinations.

The repository has prior evidence of green-but-hollow paths: declared interfaces, fake output paths, skeleton implementations, and code not reached through production callers. Release evidence must prove capability through the actual product, job, renderer, editor, export, and live-session surfaces.

Because there are no production users, a long public canary or permanent old/new dual mode adds complexity without reducing meaningful migration risk. Pre-release acceptance and rollback-safe data remain required.

## Decision

### Full-Breadth V1 ships as one release

V1 is not complete until all of the following reach one production quality bar:

- twelve core artifact surfaces;
- five Artifact Specialist families;
- four Subject Capability Packs and their declared overlays;
- K–12 policy across K–2, 3–5, 6–8, and 9–12;
- English and Vietnamese, including target/instruction language separation;
- certified MOET 2018, CCSS, and NGSS alignment where claimed;
- typed structured editing and AI rewrite for every artifact surface;
- artifact versions, `AnswerSet`, translations, required variants, review notes, approval, and dependency staleness;
- every declared renderer and export capability;
- approved slide publication to a live Teaching Session;
- durability, privacy, accessibility, observability, and operations described by the preceding ADRs.

The default run remains core four plus slide deck with recommendations. Full breadth is capability coverage, not an instruction to generate every artifact and variant for every teacher request.

### Capability-covering release matrix

Release evidence covers every declared seam exhaustively and uses pairwise or covering-array scenarios across combinatorial dimensions. It includes:

- every artifact payload and renderer plugin;
- every specialist family and adapter;
- every Subject Capability Pack and domain overlay;
- every Grade Band and both languages;
- certified curriculum lanes;
- every supported artifact/question/export matrix entry;
- explicit rejection tests for every unsupported export entry;
- canonical, translated, required variant, and teacher/student audience paths;
- manual edit, AI rewrite, restore, stale dependency, reapproval, and export regeneration;
- crash/restart/idempotent resume, cancellation, deletion, and provider/research outage;
- privacy, tenant isolation, contextual safety, answer leakage, and security abuse cases;
- Creator Workspace WCAG 2.2 AA and artifact-specific accessibility;
- browser, presentation, print, keyboard, overflow, and visual QA;
- real file validation or external import smoke for exports;
- at least one live-LLM acceptance scenario in every high-risk capability lane.

Meaningless Cartesian combinations are not invented. The Export Capability Matrix and specialist/subject capability declarations define which combinations are product claims.

### Evidence-complete issue Definition of Done

Every implementation issue must deliver an observable vertical capability and include, as applicable:

- canonical contract and Python/TypeScript parity;
- persistence and migration behavior;
- API and Creator Workspace behavior;
- specialist, renderer, quality, and export integration;
- security, privacy, safety, and accessibility checks;
- unit, integration, E2E, and manual QA through the real surface;
- durable evidence artifacts and exact verification commands;
- ADR, AGENTS, runtime snapshot, and capability-manifest sync;
- proof that no zero-caller, fake, placeholder, or skeleton path represents completion.

An issue cannot close by assuming an unimplemented blocker.

### GitHub issue structure

Work is published as one release epic/map plus dependency-linked tracer-bullet issues. Architectural enablers use expand/migrate/contract sequencing where a wide contract change cannot remain green as one slice. Product capability work is vertical: each slice connects contract, persistence, generation, rendering, quality, workspace, export, and evidence needed to demonstrate one real behavior.

Layer-only issue decomposition is avoided except for unavoidable wide refactors or shared release infrastructure.

### Big-bang GA with rollback-safe data

After the complete acceptance matrix passes, Creator V1 cuts over for all users in one deployment. There is no public partial V1, permanent old/new mode selector, or long-lived old generator feature flag.

Rollback uses deployment rollback and backward-readable data:

- database migrations expand first and remain non-destructive through stabilization;
- new Creator writes use V2 contracts only;
- the previous release can read or safely ignore new records sufficiently for service rollback;
- database and artifact backups exist before cutover;
- destructive schema and legacy-writer cleanup occurs only after the stabilization window.

### Success metrics

V1 metrics are ordered:

1. zero hard-block, answer-leakage, and privacy incidents;
2. teacher approval with no more than one material revision for target scenarios;
3. artifact and export completion reliability;
4. factual and assessment correctness evidence;
5. time to first reviewable artifact;
6. reuse, export, and live-session usage.

V1 does not claim causal student learning-outcome improvement. Outcome evidence may inform later governed changes.

## Consequences

- The release is larger and has a longer critical path than a narrow MVP.
- “Done” is unambiguous: every declared capability works through its real surface.
- Pairwise and capability-driven coverage prevents both combinatorial explosion and representative-test handwaving.
- The absence of production users simplifies deployment, but not correctness, privacy, or rollback requirements.
- GitHub issues must expose a dependency frontier so the large release can still be delivered in reviewable tracer bullets.

## Considered Options

- **Program-wide V1 with multiple partial releases**: rejected because the user explicitly chose one full-breadth V1 release.
- **Artifact breadth only**: rejected because the editor, subject, language, and export surfaces are part of the product claim.
- **Exhaustive every-permutation testing**: rejected because unsupported or meaningless combinations are not capabilities.
- **Representative E2E only**: rejected because it permits declared paths to remain hollow.
- **Progressive public beta or permanent dual mode**: rejected because no production users exist and dual architecture adds ongoing complexity.
- **No rollback because there are no users**: rejected because migrations and development data still need a safe operational path.

## References

- ADR-018 Runtime Parity and Legacy Decommission
- ADR-030 Full Artifact-Type and Export Coverage
- ADR-031 Full Output Test Matrix
- ADR-032 Verification Integrity and Engineering Discipline
- ADR-044 Slide Deck Real-LLM Acceptance Harness
- ADR-051 through ADR-057
