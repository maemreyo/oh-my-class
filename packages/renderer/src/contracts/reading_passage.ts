/**
 * Reading passage artifact data contract.
 *
 * Used by ContentCreator Agent when artifact_type == "reading_passage".
 * Rendered by pages/reading_passage.html template.
 */

export interface ComprehensionQuestion {
  id: string;
  prompt: string;
  answer: string;
  type: "mc" | "short_answer" | "essay";
  options?: { label: string; text: string }[];
}

export interface ReadingPassageData {
  title: string;
  subject: string;
  gradeLevel: string;
  passage: string;
  questions: ComprehensionQuestion[];
  theme?: string;
  lang?: string;
}
