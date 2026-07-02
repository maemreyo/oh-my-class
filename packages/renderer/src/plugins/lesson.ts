import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const componentSchema = z.object({ type: z.string().min(1) }).catchall(z.unknown());

const vocabEntrySchema = z.object({
  term: z.string().min(1),
  definition: z.string().min(1),
  partOfSpeech: z.string().optional(),
  example: z.string().optional(),
});

const lessonSectionSchema = z.object({
  heading: z.string().min(1),
  body: z.string(),
  id: z.string().optional(),
  time: z.string().optional(),
  components: z.array(componentSchema).optional(),
  teacher_only: z.unknown().optional(),
});

const lessonSidebarSchema = z.object({
  title: z.string().min(1),
  subtitle: z.string().optional(),
  stats: z.array(z.object({ key: z.string(), value: z.string() })).optional(),
  nav: z.array(z.object({ href: z.string(), num: z.string().optional(), label: z.string() })).optional(),
  linkback: z.string().optional(),
}).optional();

const lessonHeroSchema = z.object({
  eyebrow: z.string().optional(),
  lede: z.string().optional(),
  noteBox: z.string().optional(),
  statCards: z.array(z.object({ label: z.string(), value: z.string(), unit: z.string().optional() })).optional(),
  objectives: z.array(z.string()).optional(),
}).optional();

const lessonInputSchema = z.object({
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  objectives: z.array(z.string()),
  sections: z.array(lessonSectionSchema).min(1),
  vocabulary: z.array(vocabEntrySchema).optional(),
  theme: z.string().optional(),
  lang: z.string().optional(),
  sidebar: lessonSidebarSchema,
  hero: lessonHeroSchema,
});

type LessonInput = z.infer<typeof lessonInputSchema>;
type LessonComponent = z.infer<typeof componentSchema>;

type LessonTemplateData = Omit<LessonInput, "sections"> & {
  readonly sections: readonly (Omit<LessonInput["sections"][number], "components"> & { readonly components?: readonly LessonComponent[] })[];
  readonly themeCSS: string;
  readonly lang: string;
};

const lessonSanitizerPolicy = { version: "lesson-policy-v1", config: "quiz" } as const;

function projectQuestionCardForStudent(component: LessonComponent): LessonComponent {
  const { answer: _answer, explain: _explain, wrong_reasons: _wrongReasons, ...studentComponent } = component;
  return studentComponent;
}

function projectComponentForStudent(component: LessonComponent): LessonComponent {
  switch (component.type) {
    case "question_card":
      return projectQuestionCardForStudent(component);
    case "question_list": {
      const questions = Array.isArray(component.questions) ? component.questions.filter((question) => componentSchema.safeParse(question).success) : [];
      return { ...component, questions: questions.map((question) => projectQuestionCardForStudent(componentSchema.parse(question))) };
    }
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
        rows: Array.isArray(component.rows)
          ? component.rows.map((row) => {
              if (row === null || typeof row !== "object") return row;
              const { teacher_rationale: _teacherRationale, ...studentRow } = row;
              return studentRow;
            })
          : component.rows,
      };
    default:
      return component;
  }
}

function projectLessonForStudent(lesson: LessonInput): LessonTemplateData["sections"] {
  return lesson.sections
    .filter((section) => section.teacher_only !== true)
    .map((section) => ({
      ...section,
      components: section.components?.map(projectComponentForStudent),
    }));
}

function adaptLesson(input: unknown, context: RenderContext, services: RenderServices): LessonTemplateData {
  const lesson = lessonInputSchema.parse(input);
  return {
    ...lesson,
    lang: lesson.lang ?? context.locale,
    themeCSS: services.themeCss,
    sections: context.audience === "student" ? projectLessonForStudent(lesson) : lesson.sections,
  };
}

export const lessonPlugin: ArtifactKindPlugin<LessonTemplateData> = {
  kind: "lesson",
  version: "0.1.0",
  templateVersion: "lesson-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: lessonInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: lessonSanitizerPolicy,
  adapt: adaptLesson,
  templatePath: () => "pages/lesson",
};
