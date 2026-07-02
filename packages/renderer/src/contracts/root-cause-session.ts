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
