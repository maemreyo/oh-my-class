/**
 * ContentComponent discriminated union — TypeScript side.
 *
 * Mirrors common/contracts/components/ Python Pydantic models.
 * Python Pydantic is canonical; this is the TS equivalent for rendering.
 */

export interface HeadingComponent {
  type: "heading";
  level: 1 | 2 | 3 | 4;
  text: string;
  id?: string;
}

export interface ParagraphComponent {
  type: "paragraph";
  text: string;
}

export interface CalloutComponent {
  type: "callout";
  variant: "note" | "warning" | "tip" | "alert";
  title?: string;
  body: string;
}

export interface TableComponent {
  type: "table";
  columns: string[];
  rows: string[][];
  caption?: string;
}

export interface StatCard {
  label: string;
  value: string;
  variant?: "target" | "now" | "default";
}

export interface StatGridComponent {
  type: "stat_grid";
  stats: StatCard[];
}

export interface PatternCard {
  id: string;
  group: string;
  title: string;
  description: string;
}

export interface PatternGridComponent {
  type: "pattern_grid";
  patterns: PatternCard[];
}

export interface TraitCard {
  icon: string;
  title: string;
  body: string;
}

export interface TraitGridComponent {
  type: "trait_grid";
  traits: TraitCard[];
}

export interface TaxonomyItem {
  icon: string;
  title: string;
  body: string;
  example: string;
}

export interface TaxonomyGridComponent {
  type: "taxonomy_grid";
  items: TaxonomyItem[];
}

export interface PhaseBlock {
  label: string;
  items?: string[];
  text?: string;
  full?: boolean;
}

export interface RoadmapPhase {
  title: string;
  when: string;
  goal?: string;
  blocks?: PhaseBlock[];
  output?: string;
  group?: string;
}

export interface PhaseTimelineComponent {
  type: "phase_timeline";
  phases: RoadmapPhase[];
}

export interface FlowItem {
  time: string;
  title: string;
  body: string;
}

export interface FlowStepComponent {
  type: "flow_step";
  steps: FlowItem[];
}

export interface QuestionCardComponent {
  type: "question_card";
  id: number | string;
  text: string;
  options: Record<string, string>;
  answer: string;
  explain: string;
  group?: string;
  wrong_reasons?: Record<string, string>;
  essence?: string;
  tip?: string;
}

export interface QuestionListComponent {
  type: "question_list";
  questions: QuestionCardComponent[];
  section_key?: string;
  group?: string;
  title?: string;
  sub?: string;
  instruction?: string;
  summary?: string;
  range?: string;
}

export interface ConceptMapComponent {
  type: "concept_map";
  nodes: { id: string; label: string }[];
}

export interface TimelineComponentData {
  type: "timeline";
  events: { time: string; label: string }[];
}

export interface AlertComponent {
  type: "alert";
  variant?: "info" | "warning" | "error" | "success";
  title?: string;
  body: string;
}

export type ContentComponent =
  | HeadingComponent
  | ParagraphComponent
  | CalloutComponent
  | TableComponent
  | StatGridComponent
  | PatternGridComponent
  | TraitGridComponent
  | TaxonomyGridComponent
  | PhaseTimelineComponent
  | FlowStepComponent
  | QuestionCardComponent
  | QuestionListComponent
  | ConceptMapComponent
  | TimelineComponentData
  | AlertComponent
  | { type: string; [key: string]: unknown };
