/**
 * Answer key artifact data contract.
 *
 * Used by ContentCreator Agent when artifact_type == "answer_key".
 * Rendered by pages/answer_key.html template.
 * Teacher-only view — answers are always visible.
 */

import type { MCQuestion } from "./quiz.js";

export interface AnswerKeyData {
  title: string;
  subject: string;
  gradeLevel: string;
  questions: MCQuestion[];
  teachingNotes?: string[];
  rubric?: string;
  theme?: string;
  lang?: string;
}
