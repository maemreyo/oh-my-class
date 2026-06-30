import { inspect } from "node:util";

import type { ContentComponent } from "./contracts/index.js";

type ArtifactRecord = Readonly<Record<string, unknown>>;

const KNOWN_COMPONENT_TYPES = [
  "heading",
  "paragraph",
  "callout",
  "table",
  "stat_grid",
  "pattern_grid",
  "trait_grid",
  "taxonomy_grid",
  "phase_timeline",
  "flow_step",
  "question_card",
  "question_list",
  "concept_map",
  "timeline",
  "alert",
  "vocab_cluster",
  "contrastive_pairs",
  "phrasal_verb_cluster",
  "film_clip_activity",
  "roleplay_script",
  "active_recall_prompt",
  "hw_list",
] as const satisfies readonly ContentComponent["type"][];

type KnownComponentType = (typeof KNOWN_COMPONENT_TYPES)[number];
type MissingComponentType = Exclude<ContentComponent["type"], KnownComponentType>;
export const componentRegistryCoversUnion: MissingComponentType extends never ? true : never = true;

const KNOWN_COMPONENT_TYPE_SET: ReadonlySet<string> = new Set(KNOWN_COMPONENT_TYPES);

export class UnknownContentComponentError extends Error {
  readonly componentType: string;
  readonly sectionId: string;

  constructor(componentType: string, sectionId: string) {
    super(`Unknown content component type '${componentType}' in section '${sectionId}'`);
    this.name = "UnknownContentComponentError";
    this.componentType = componentType;
    this.sectionId = sectionId;
  }
}

function asRecord(value: unknown): ArtifactRecord {
  return value !== null && typeof value === "object" ? value as ArtifactRecord : {};
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function sectionId(section: ArtifactRecord, fallback: string): string {
  return asString(section.id, fallback);
}

export function preserveComponents(section: ArtifactRecord, fallbackSectionId: string): readonly ContentComponent[] {
  const raw = section.components;
  if (!Array.isArray(raw)) return [];
  return raw.map((component) => parseContentComponent(component, sectionId(section, fallbackSectionId)));
}

function parseContentComponent(component: unknown, sourceSectionId: string): ContentComponent {
  if (isContentComponent(component)) {
    return component;
  }
  const record = asRecord(component);
  const componentType = asString(record.type, inspect(component));
  throw new UnknownContentComponentError(componentType, sourceSectionId);
}

function isContentComponent(value: unknown): value is ContentComponent {
  if (value === null || typeof value !== "object" || !("type" in value)) {
    return false;
  }
  return typeof value.type === "string" && KNOWN_COMPONENT_TYPE_SET.has(value.type);
}

function projectQuestionCardForStudent(component: ContentComponent & { type: "question_card" }): ContentComponent & { type: "question_card" } {
  const { answer: _answer, explain: _explain, wrong_reasons: _wrongReasons, ...studentComponent } = component;
  return studentComponent;
}

function projectComponentForStudent(component: ContentComponent): ContentComponent {
  switch (component.type) {
    case "question_card":
      return projectQuestionCardForStudent(component);
    case "question_list":
      return {
        ...component,
        questions: component.questions.map(projectQuestionCardForStudent),
      };
    case "roleplay_script": {
      const { answer_key: _answerKey, coaching_notes: _coachingNotes, ...studentComponent } = component;
      return studentComponent;
    }
    case "active_recall_prompt": {
      const { reveal_answer: _revealAnswer, teacher_rationale: _teacherRationale, ...studentComponent } = component;
      return studentComponent;
    }
    case "contrastive_pairs":
      return {
        ...component,
        rows: component.rows?.map(({ teacher_rationale: _teacherRationale, ...row }) => row),
      };
    case "heading":
    case "paragraph":
    case "callout":
    case "table":
    case "stat_grid":
    case "pattern_grid":
    case "trait_grid":
    case "taxonomy_grid":
    case "phase_timeline":
    case "flow_step":
    case "concept_map":
    case "timeline":
    case "alert":
    case "vocab_cluster":
    case "phrasal_verb_cluster":
    case "film_clip_activity":
    case "hw_list":
      return component;
    default:
      return assertNeverComponent(component);
  }
}

function assertNeverComponent(component: never): never {
  throw new Error(`Unhandled content component projection: ${inspect(component)}`);
}

export function preserveStudentComponents(section: ArtifactRecord, fallbackSectionId: string): readonly ContentComponent[] {
  return preserveComponents(section, fallbackSectionId).map(projectComponentForStudent);
}
