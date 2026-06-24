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

export type ArtifactDataMap = {
  lesson: LessonData;
  quiz: QuizData;
  drill: DrillData;
  worksheet: WorksheetData;
  recap: RecapData;
  infographic: InfographicData;
  answer_key: AnswerKeyData;
  flashcard_deck: FlashcardDeckData;
  reading_passage: ReadingPassageData;
  exit_ticket: ExitTicketData;
};

export type ArtifactType = keyof ArtifactDataMap;

// Re-export all individual types for convenience
export type { LessonData, LessonSection, VocabEntry } from "./lesson.js";
export type { QuizData, MCQuestion } from "./quiz.js";
export type { DrillData, DrillQuestion } from "./drill.js";
export type { WorksheetData, WorksheetSection } from "./worksheet.js";
export type { RecapData, RecapItem } from "./recap.js";
export type { InfographicData, InfographicSection } from "./infographic.js";
export type { AnswerKeyData } from "./answer_key.js";
export type { FlashcardDeckData, Flashcard } from "./flashcard_deck.js";
export type { ReadingPassageData, ComprehensionQuestion } from "./reading_passage.js";
export type { ExitTicketData, ExitTicketQuestion } from "./exit_ticket.js";
