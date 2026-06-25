/**
 * Artifact data contracts — typed registry (T3).
 *
 * Each artifact type maps to its own data interface.
 * `ArtifactDataMap` is the single source of truth for the renderer's
 * generic `renderArtifact<T>()` function.
 */

import type { LessonData } from "./lesson.js";
import type { QuizData } from "./quiz.js";
import type { DrillData } from "./drill.js";
import type { WorksheetData } from "./worksheet.js";
import type { RecapData } from "./recap.js";
import type { InfographicData } from "./infographic.js";
import type { AnswerKeyData } from "./answer_key.js";
import type { FlashcardDeckData } from "./flashcard_deck.js";
import type { ReadingPassageData } from "./reading_passage.js";
import type { ExitTicketData } from "./exit_ticket.js";
import type { TeachingPackData } from "./schemas/teaching-pack.js";
import type { RoadmapData } from "./roadmap.js";

export type ArtifactDataMap = {
  lesson:          LessonData;
  quiz:            QuizData;
  drill:           DrillData;
  worksheet:       WorksheetData;
  recap:           RecapData;
  infographic:     InfographicData;
  answer_key:      AnswerKeyData;
  flashcard_deck:  FlashcardDeckData;
  reading_passage: ReadingPassageData;
  exit_ticket:     ExitTicketData;
  teaching_pack:   TeachingPackData;   // TP1: type 11 — bundle artifact
  roadmap:         RoadmapData;        // R08: personalized learning roadmap
};

export type ArtifactType = keyof ArtifactDataMap;

// Re-export all individual types for convenience
export type { LessonData, LessonSection, VocabEntry } from "./lesson.js";
export type { QuizData, MCQuestion } from "./quiz.js";
export type { DrillData, DrillQuestion } from "./drill.js";
export type { WorksheetData, WorksheetSection } from "./worksheet.js";
export type { RecapData, RecapItem } from "./recap.js";
export type { InfographicData, InfographicSection } from "./infographic.js";
export type { AnswerKeyData, AnswerKeySection, AnswerKeyMetadata } from "./answer_key.js";
export type { FlashcardDeckData, Flashcard } from "./flashcard_deck.js";
export type { ReadingPassageData, ComprehensionQuestion } from "./reading_passage.js";
export type { ExitTicketData, ExitTicketQuestion } from "./exit_ticket.js";
export type { TeachingPackData } from "./schemas/teaching-pack.js";
export type { RoadmapData, RoadmapHero, RoadmapSidebar, RoadmapSection, StatCard as RoadmapStatCard } from "./roadmap.js";
export type { ContentComponent, QuestionCardComponent, QuestionListComponent } from "./components.js";

// ── New schemas (Report 07) ───────────────────────────────────────────────────
export type { CurriculumFramework, CurriculumStandard } from "./curriculum-standard.js";
export type {
  LessonPlan, LessonPhase, GagneEvent,
  LearningObjective, DesiredResults, AssessmentEvidence,
  PerformanceTask, VocabularyTerm, DifferentiationGuide,
} from "./schemas/lesson-plan.js";
export type {
  Worksheet as WorksheetSchema, WorksheetSection as WorksheetSectionSchema,
  WorksheetBlock, MediaAttachment,
} from "./schemas/worksheet.js";
export type {
  QualityScore, TechnicalScore, PedagogicalScore,
} from "./schemas/teaching-pack.js";
export type {
  FullInfographic, FullInfographicSection, ColorTheme, DiagramData,
  DiagramNode, DiagramEdge,
} from "./schemas/infographic.js";
