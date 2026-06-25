/**
 * Lesson artifact data contract.
 *
 * Used by ContentCreator Agent when artifact_type == "lesson".
 * Rendered by pages/lesson.html template.
 */

export interface LessonSidebarStat {
  key: string;
  value: string;
}

export interface LessonSidebarNavItem {
  href: string;
  num?: string;
  label: string;
}

export interface LessonSidebar {
  title: string;
  subtitle?: string;
  stats?: LessonSidebarStat[];
  nav?: LessonSidebarNavItem[];
  linkback?: string;
}

export interface LessonHeroStat {
  label: string;
  value: string;
  unit?: string;
}

export interface LessonHero {
  eyebrow?: string;
  lede?: string;
  noteBox?: string;
  statCards?: LessonHeroStat[];
  objectives?: string[];
}

export interface LessonSection {
  heading: string;
  body: string;
  id?: string;
  time?: string;
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
  sidebar?: LessonSidebar;
  hero?: LessonHero;
}
