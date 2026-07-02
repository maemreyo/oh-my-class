---
title: Define RootCauseSessionData contract
status: ready-for-agent
labels: [renderer, contracts, root-cause, paper-dossier]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## Why this issue exists

Issue 003 specifies a `root-cause-session.html` Eta template for the paper-dossier family.
Issue 004's paper-dossier adapter says it must "transform root-cause transcript data into
template data." But neither issue defines where `RootCauseSessionData` lives, what shape it
takes, or what existing contract (if any) it extends.

This issue closes that gap with an explicit contract type before Issues 003 and 004 can bind
against it.

## What to build

Create `packages/renderer/src/contracts/root-cause-session.ts`:

```typescript
/**
 * Root-cause / Socratic session dossier contract.
 *
 * A structured investigation artifact built around elimination and causal
 * reasoning: the teacher poses a symptom, the session walks through anchor
 * moments, controlled comparisons, and a generalization checkpoint.
 *
 * This type is consumed exclusively by renderArtifactUi() with the
 * paper-dossier family. It is NOT added to ArtifactDataMap (see ADR-024
 * and Issue 014 design note).
 */
export interface RootCauseSessionData {
  // ── Cover ──────────────────────────────────────────────────────────────────
  title: string;
  subtitle?: string;
  subject: string;
  gradeLevel: string;
  lang: "vi" | "en";
  theme?: string;

  // ── Session meta ───────────────────────────────────────────────────────────
  sessionCode: string;           // e.g. "RC-U2-L3"
  difficulty: "low" | "mid" | "high";
  estimatedMinutes: number;
  targetConcept: string;         // the concept being diagnosed/corrected

  // ── Content sections (ordered) ────────────────────────────────────────────
  anchorTimeline: AnchorTimelineEntry[];
  comparisons: ControlledComparison[];
  scenarioAnchors?: ScenarioAnchor[];
  generalizationCheckpoints: GeneralizationCheckpoint[];
  stressTests?: StressTest[];
  metaphorLogs?: MetaphorLog[];

  // ── Footer ─────────────────────────────────────────────────────────────────
  masteryMarkers?: MasteryMarker[];
  teacherNotes?: string;         // teacher-only; adapter gates on audience
}

export interface AnchorTimelineEntry {
  id: string;
  label: string;         // short phase label (e.g. "T+0", "Week 3")
  event: string;         // what happened at this anchor
  significance: string;  // why it matters for root-cause reasoning
  isKeyAnchor?: boolean; // rendered with emphasis on the SVG axis
}

export interface ControlledComparison {
  id: string;
  constant: string;      // what is held fixed across all variants
  variants: ComparisonVariant[];
  insight: string;       // what the comparison reveals
}

export interface ComparisonVariant {
  label: string;
  value: string;
  isControl?: boolean;   // rendered as reference band in art-controlled-comparison
}

export interface ScenarioAnchor {
  id: string;
  scenario: string;      // vivid, concrete scenario opener
  connection: string;    // how this scenario anchors the abstract concept
}

export interface GeneralizationCheckpoint {
  id: string;
  learnerClaim: string;  // the claim being tested (student's tentative generalization)
  verdict: "confirmed" | "refined" | "rejected";
  evidence: string;      // what evidence drives the verdict
  refinedClaim?: string; // if verdict === 'refined', the improved statement
}

export interface StressTest {
  id: string;
  brokenExample: string;
  whyItBreaks: string;
  fix?: string;
}

export interface MetaphorLog {
  id: string;
  landedAttempt: string;        // the metaphor that worked
  collapsedAttempts?: string[]; // earlier attempts (hidden behind disclosure)
}

export interface MasteryMarker {
  label: string;
  level: "aware" | "applying" | "mastered";
}
```

## Acceptance criteria

- [ ] `src/contracts/root-cause-session.ts` exists with all types above
- [ ] `RootCauseSessionData` is NOT exported from `src/contracts/index.ts`'s `ArtifactDataMap`
- [ ] `RootCauseSessionData` IS re-exported from `src/contracts/index.ts` as a named type (for convenience imports)
- [ ] All fields use plain TypeScript interfaces (no Zod, no runtime validation — adapters validate at call site)
- [ ] `teacherNotes` field is documented as teacher-only (adapter gates on audience)
- [ ] `pnpm --filter @oh-my-class/renderer typecheck` → no type errors

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/root-cause-session-contract.test.ts`:
  - Contract shape compiles with a valid mock object (compile-time only, no assertions needed)
  - `AnchorTimelineEntry` requires `id`, `label`, `event`, `significance`
  - `GeneralizationCheckpoint` `verdict` is a union literal, not `string`
  - `RootCauseSessionData` can be constructed without optional fields

## Verification

- `pnpm --filter @oh-my-class/renderer typecheck` → no type errors
- Manual: import `RootCauseSessionData` in a test file, construct a minimal object, verify TypeScript accepts it

## Blocked by

None — pure TypeScript interface, no runtime dependencies.

## Design notes

### Why not in ArtifactDataMap?

See Issue 014 design note. Root-cause session is a rendering concern (paper-dossier family),
not a schema-layer artifact type. It does not go through `renderArtifact()` and never needs
a sanitizer config via the typed `ArtifactType` path.

### Why not reuse LessonData?

Root-cause sessions have a fundamentally different section schema: `anchorTimeline[]`,
`comparisons[]`, `generalizationCheckpoints[]` — none of which map to `LessonSection`.
Reusing `LessonData` would require `sections: unknown[]` or a discriminated union that
adds complexity without benefit. A dedicated interface is cleaner and independently
testable.

### Why `"vi" | "en"` literal for lang?

Artifact UI templates use `lang` to set the `<html lang="">` attribute and to apply
Vietnamese-specific typography rules (diacritic-safe line-height, sentence case for labels).
Narrowing to the two supported locales catches misconfiguration at compile time rather than
silently producing incorrect output.
