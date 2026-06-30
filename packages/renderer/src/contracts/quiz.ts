/**
 * Quiz artifact data contract.
 *
 * Used by ContentCreator Agent when artifact_type == "quiz".
 * Rendered by pages/quiz.html template.
 */

export interface MCQuestion {
  id: string;
  prompt: string;
  options: { label: string; text: string }[];
  answer: string;
  explain?: string;
  timeMinutes?: number;
}

export interface QuizData {
  title: string;
  subject: string;
  gradeLevel: string;
  timeLimit?: number;
  questions: MCQuestion[];
  theme?: string;
  lang?: string;
}
