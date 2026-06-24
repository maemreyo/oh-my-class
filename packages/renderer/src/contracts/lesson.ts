/**
 * Lesson artifact data contract.
 *
 * Used by ContentCreator Agent when artifact_type == "lesson".
 * Rendered by pages/lesson.html template.
 */

export interface LessonSection {
  heading: string;
  body: string;
  components?: string[];
}

export interface VocabEntry {
  term: string;
  definition: string;
  partOfSpeech?: string;
  example?: string;
}

export interface LessonData {
  title: string;
  subject: string;
  gradeLevel: string;
  objectives: string[];
  sections: LessonSection[];
  vocabulary?: VocabEntry[];
  theme?: string;
  lang?: string;
}
