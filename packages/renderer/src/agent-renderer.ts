import process from "node:process";
import { randomUUID } from "node:crypto";
import { ArtifactContentSchema } from "@oh-my-class/schemas/generated/artifact.js";

import { preserveComponents, preserveStudentComponents } from "./agent-component-projection.js";
import { runWorkerLoop } from "./agent-worker.js";
import { render } from "./core/render.js";
import { renderArtifact } from "./renderer.js";
import type {
  AnswerKeyData,
  DrillData,
  InfographicData,
  LessonData,
  QuizData,
  RecapData,
  SlideDeckData,
  WorksheetData,
} from "./contracts/index.js";
import type { RenderContext } from "./core/types.js";

export { isContentComponent, UnknownContentComponentError } from "./agent-component-projection.js";

type ArtifactRecord = Readonly<Record<string, unknown>>;

function asRecord(value: unknown): ArtifactRecord {
  return value !== null && typeof value === "object" ? value as ArtifactRecord : {};
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function asRecordArray(value: unknown): readonly ArtifactRecord[] {
  return Array.isArray(value) ? value.map(asRecord) : [];
}

function common(artifact: ArtifactRecord): Pick<LessonData, "title" | "subject" | "gradeLevel" | "theme" | "lang"> {
  const metadata = asRecord(artifact.metadata);
  const accessibility = asRecord(artifact.accessibility);
  return {
    title: asString(artifact.title, "Untitled Teaching Pack"),
    subject: asString(metadata.subject, "General"),
    gradeLevel: asString(metadata.grade_level, asString(metadata.gradeLevel, "Grade")),
    theme: asString(artifact.theme, "default"),
    lang: asString(accessibility.language, "vi"),
  };
}

function lessonData(artifact: ArtifactRecord): LessonData {
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  const objectives = sections
    .filter((section) => asString(section.type) === "objective")
    .map((section) => asString(section.content));
  return {
    ...common(artifact),
    objectives,
    sections: sections.map((section, index) => ({
      heading: asString(section.title, `Section ${index + 1}`),
      body: asString(section.content, asString(section.text, "")),
      id: asString(section.id, `section-${index + 1}`),
      time: asString(section.time, ""),
      components: preserveStudentComponents(section, `section-${index + 1}`),
    })),
    hero: {
      eyebrow: asString(artifact.artifact_type, "lesson"),
      lede: asString(asRecord(artifact.metadata).summary, "A structured oh-my-class lesson pack."),
      objectives,
    },
  };
}

function worksheetData(artifact: ArtifactRecord): WorksheetData {
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  return {
    ...common(artifact),
    sections: sections.map((section, index) => {
      const explicitQuestions = asRecordArray(section.questions);
      // Direct question_card items inside section.components
      const componentCards = asRecordArray(section.components)
        .filter((c) => asString(c.type) === "question_card");
      // question_card items nested inside question_list containers
      const listCards = asRecordArray(section.components)
        .filter((c) => asString(c.type) === "question_list")
        .flatMap((list) => asRecordArray(list.questions).filter((q) => asString(q.type) === "question_card"));
      const allCards = componentCards.length > 0 ? componentCards : listCards;
      const questions = explicitQuestions.length > 0
        ? explicitQuestions.map((question, questionIndex) => ({
            id: asString(question.id, `w${index + 1}-${questionIndex + 1}`),
            prompt: asString(question.prompt, asString(question.content, "Write your answer.")),
            type: asString(question.type, "short_answer"),
          }))
        : allCards.length > 0
          ? allCards.map((card, cardIndex) => ({
              id: asString(card.id, `w${index + 1}-${cardIndex + 1}`),
              prompt: asString(card.text, asString(card.content, "Write your answer.")),
              type: "short_answer",
            }))
          : [{
              id: `w${index + 1}-1`,
              prompt: asString(section.content, "Complete this practice task."),
              type: "short_answer",
            }];
      return { title: asString(section.title, `Practice ${index + 1}`), questions };
    }),
  };
}

function optionList(optionsValue: unknown): { label: string; text: string }[] {
  const options = asRecord(optionsValue);
  const labels = ["A", "B", "C", "D"];
  return labels.map((label) => ({
    label,
    text: asString(options[label], label),
  }));
}

function quizAnswer(section: ArtifactRecord): string {
  return asString(
    section.answer,
    asString(
      section.correct_answer,
      asString(section.correctAnswer, asString(section.correct_option, asString(section.correctOption, "—"))),
    ),
  );
}

function quizExplanation(section: ArtifactRecord): string {
  return asString(section.explain, asString(section.explanation, asString(section.rationale)));
}

function quizData(artifact: ArtifactRecord): QuizData {
  const rawSections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  // Component-based structure: question_card items nested inside container sections.
  // Flatten them so both the legacy flat format and the nested format render correctly.
  const questionSections = rawSections.flatMap((section) => {
    const cards = asRecordArray(section.components).filter((c) => asString(c.type) === "question_card");
    return cards.length > 0 ? cards : [section];
  });
  return {
    ...common(artifact),
    timeLimit: 10,
    questions: questionSections.map((section, index) => ({
      id: asString(section.id, `q${index + 1}`),
      prompt: asString(section.prompt, asString(section.content, asString(section.text, "Question"))),
      options: optionList(section.options),
      answer: quizAnswer(section),
      explain: quizExplanation(section),
    })),
  };
}

function drillData(artifact: ArtifactRecord): DrillData {
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  return {
    ...common(artifact),
    timeLimit: 10,
    questions: sections.map((section, index) => ({
      id: asString(section.id, `d${index + 1}`),
      prompt: asString(section.prompt, asString(section.content, asString(section.text, "Practice question"))),
      answer: quizAnswer(section),
      type: asString(section.type, "fill") === "question_card" ? "mc" : "fill",
      options: optionList(section.options),
    })),
  };
}

function recapData(artifact: ArtifactRecord): RecapData {
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  return {
    ...common(artifact),
    items: sections.map((section, index) => ({
      id: asString(section.id, `recap-${index + 1}`),
      concept: asString(section.title, `Concept ${index + 1}`),
      summary: asString(section.content, asString(section.summary, "Review this concept.")),
    })),
  };
}

function infographicData(artifact: ArtifactRecord): InfographicData {
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  return {
    ...common(artifact),
    sections: sections.map((section, index) => ({
      title: asString(section.title, `Visual ${index + 1}`),
      content: asString(section.content, asString(section.summary, "")),
    })),
  };
}

function answerKeyData(artifact: ArtifactRecord): AnswerKeyData {
  const sections = asRecordArray(artifact.sections);
  return {
    title: common(artifact).title,
    theme: common(artifact).theme,
    accessibility: { language: common(artifact).lang },
    sections: sections.map((section, index) => ({
      id: asString(section.id, `answer-${index + 1}`),
      title: asString(section.title, `Answer ${index + 1}`),
      summary: asString(section.content, asString(section.summary, "")),
      components: [...preserveComponents(section, `answer-${index + 1}`)],
    })),
  };
}

function slideDeckData(artifact: ArtifactRecord): SlideDeckData {
  const metadataDeck = asRecord(asRecord(artifact.metadata).slide_deck_data);
  if (Object.keys(metadataDeck).length > 0) {
    return metadataDeck as SlideDeckData;
  }
  const sectionDeck = asRecord(asRecordArray(artifact.sections)[0]?.slide_deck);
  return sectionDeck as SlideDeckData;
}

function makeContext(audience: RenderContext["audience"], lang: string): RenderContext {
  return {
    audience,
    locale: lang === "en" ? "en" : "vi",
    theme: "default",
    renderMode: "preview",
    requestId: randomUUID(),
    versions: { rendererVersion: "0.1.0" },
    assetPolicy: "inline-only",
  };
}

export async function renderAgentArtifact(input: unknown): Promise<string> {
  const artifact = ArtifactContentSchema.parse(input);
  const artifactType = asString(artifact.artifact_type, "lesson");
  const lang = asString(asRecord(asRecord(artifact).accessibility).language, "vi");

  switch (artifactType) {
    case "quiz":
      return render({ kind: "quiz", input: quizData(artifact), context: makeContext("student", lang) }).then((r) => r.html);
    case "worksheet":
      return render({ kind: "worksheet", input: worksheetData(artifact), context: makeContext("student", lang) }).then((r) => r.html);
    case "drill":
      return render({ kind: "drill", input: drillData(artifact), context: makeContext("student", lang) }).then((r) => r.html);
    case "recap":
      return render({ kind: "recap", input: recapData(artifact), context: makeContext("student", lang) }).then((r) => r.html);
    case "infographic":
      return render({ kind: "infographic", input: infographicData(artifact), context: makeContext("student", lang) }).then((r) => r.html);
    case "answer_key":
      return render({ kind: "answer_key", input: answerKeyData(artifact), context: makeContext("teacher", lang) }).then((r) => r.html);
    case "slide_deck":
      return renderArtifact("slide_deck", slideDeckData(artifact));
    default:
      return render({ kind: "lesson", input: lessonData(artifact), context: makeContext("student", lang) }).then((r) => r.html);
  }
}

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk)));
  }
  return Buffer.concat(chunks).toString("utf8");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  if (process.argv.includes("--worker")) {
    await runWorkerLoop();
  } else {
    const raw = await readStdin();
    const html = await renderAgentArtifact(JSON.parse(raw));
    process.stdout.write(html);
  }
}
