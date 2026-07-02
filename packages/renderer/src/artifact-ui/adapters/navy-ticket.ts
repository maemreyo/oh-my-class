/**
 * Navy-Ticket adapter.
 *
 * Converts SemanticAnchorCluster + PracticeSet into the template data shape
 * for the four navy-ticket projections. Projection safety is enforced here:
 * teacher-only fields (teacherScript, sourceNotes, edgeCases) are stripped
 * from the student variant — they never enter the template (ADR-022).
 */

import type { AnchorCard, PracticeItem, PracticeSet, SemanticAnchorCluster } from "@oh-my-class/schemas";

export type NavyTicketAudience = "teacher" | "student";
export type NavyTicketKind = "teaching" | "practice";

interface NavyTicketTermData {
  word: string;
  impression: string;
  coreTrigger: string;
  visualCue: string;
  studentExplanation: string;
  example: string;
  contrastNote: string;
  // Teacher-only — absent in student projections
  teacherScript?: string;
  sourceNotes?: string;
  edgeCases?: string;
}

interface NavyTicketPracticeItem {
  intent: string;
  prompt: string;
  options?: string[];
  // Teacher-only — absent in student projections
  answer?: string;
  rationale?: string;
}

export interface NavyTicketTeachingTemplateData {
  artifactCss: string;
  lang: string;
  groupLabel: string;
  title: string;
  subtitle: string;
  accentCat: string;
  terms: NavyTicketTermData[];
}

export interface NavyTicketPracticeTemplateData {
  artifactCss: string;
  lang: string;
  groupLabel: string;
  title: string;
  items: NavyTicketPracticeItem[];
}

function mapAnchor(anchor: AnchorCard, audience: NavyTicketAudience): NavyTicketTermData {
  const base: NavyTicketTermData = {
    word: anchor.word,
    impression: anchor.impression_vi,
    coreTrigger: anchor.core_trigger_en,
    visualCue: anchor.visual_cue_vi,
    studentExplanation: anchor.student_explanation_vi,
    example: anchor.example_en,
    contrastNote: anchor.contrast_note_vi,
  };
  if (audience === "teacher") {
    base.teacherScript = anchor.teacher_script_vi;
    base.sourceNotes = anchor.source_notes.join(" · ");
    base.edgeCases = anchor.edge_cases.join(" · ");
  }
  return base;
}

const intentLabels: Record<string, string> = {
  core_trigger_recall: "Nhận diện từ khoá cốt lõi",
  context_discrimination: "Phân biệt theo ngữ cảnh",
  boundary_explanation: "Giải thích ranh giới",
  reverse_retrieval: "Truy hồi ngược",
};

function mapPracticeItem(item: PracticeItem, audience: NavyTicketAudience): NavyTicketPracticeItem {
  const base: NavyTicketPracticeItem = {
    intent: intentLabels[item.intent] ?? item.intent,
    prompt: item.prompt,
  };
  if (audience === "teacher") {
    base.answer = item.answer;
    base.rationale = item.rationale;
  }
  return base;
}

export function adaptNavyTicketTeaching(
  cluster: SemanticAnchorCluster,
  audience: NavyTicketAudience,
  artifactCss: string,
  lang = "vi",
): NavyTicketTeachingTemplateData {
  return {
    artifactCss,
    lang,
    groupLabel: cluster.cluster_id,
    title: cluster.title,
    subtitle: cluster.contrast_notes.join(" · "),
    accentCat: "cat1",
    terms: cluster.anchors.map((a) => mapAnchor(a, audience)),
  };
}

export function adaptNavyTicketPractice(
  cluster: SemanticAnchorCluster,
  practiceSet: PracticeSet,
  audience: NavyTicketAudience,
  artifactCss: string,
  lang = "vi",
): NavyTicketPracticeTemplateData {
  return {
    artifactCss,
    lang,
    groupLabel: cluster.cluster_id,
    title: cluster.title,
    items: practiceSet.items.map((i) => mapPracticeItem(i, audience)),
  };
}
