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
  answer?: string;
  explain?: string;
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

export interface VocabItem { word: string; definition: string; example?: string }
export interface VocabClusterComponent { type: "vocab_cluster"; title: string; description?: string; items?: VocabItem[]; discrimination_prompt?: string }
export interface ContrastivePairRow { terms: string; distinction: string; example?: string; non_example?: string; boundary_note?: string; teacher_rationale?: string }
export interface ContrastivePairsComponent { type: "contrastive_pairs"; title?: string; left_label?: string; right_label?: string; rows?: ContrastivePairRow[] }
export interface PhrasalVerbItem { verb: string; meaning: string; example?: string }
export interface PhrasalVerbGroup { label: string; color?: string; items?: PhrasalVerbItem[] }
export interface PhrasalVerbClusterComponent { type: "phrasal_verb_cluster"; groups?: PhrasalVerbGroup[] }
export interface FilmClip { title: string; description: string }
export interface FilmClipActivityComponent { type: "film_clip_activity"; clips?: FilmClip[]; hunt_chips?: string[]; post_viewing_note?: string; clip_context?: string; pre_watch_prompt?: string; while_watch_task?: string; post_watch_reflection?: string; video_reference?: string }
export interface RoleplayLine { speaker: string; speaker_class?: string; text: string; cue?: string }
export interface RoleplayScriptComponent { type: "roleplay_script"; lines?: RoleplayLine[]; answer_key?: string[]; instruction?: string; confidence_scaffold?: string; coaching_notes?: string[] }
export interface ActiveRecallPromptComponent { type: "active_recall_prompt"; instruction: string; time_minutes?: number; scaffold_hint?: string; reveal_answer?: string; teacher_rationale?: string; reflection_note?: string }
export interface HwItem { tag: string; text: string }
export interface HwListComponent { type: "hw_list"; items?: HwItem[]; callout?: string }

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
  | VocabClusterComponent
  | ContrastivePairsComponent
  | PhrasalVerbClusterComponent
  | FilmClipActivityComponent
  | RoleplayScriptComponent
  | ActiveRecallPromptComponent
  | HwListComponent;
