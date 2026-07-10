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
  ExitTicketData,
  LessonData,
  QuizData,
  ReadingPassageData,
  RecapData,
  RoadmapData,
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

function drillAnswer(section: ArtifactRecord): string {
  return asString(
    section.answer,
    asString(
      section.correct_answer,
      asString(section.correctAnswer, asString(section.correct_option, asString(section.correctOption, "—"))),
    ),
  );
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
      answer: drillAnswer(section),
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

function roadmapData(artifact: ArtifactRecord): RoadmapData {
  const metadata = asRecord(artifact.metadata);
  const hero = asRecord(metadata.hero);
  const sidebar = asRecord(metadata.sidebar);
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  return {
    title: asString(artifact.title, "Learning Roadmap"),
    theme: asString(artifact.theme, "default"),
    hero: {
      eyebrow: asString(hero.eyebrow),
      title: asString(hero.title, asString(artifact.title, "Learning Roadmap")),
      lede: asString(hero.lede),
      stats: asRecordArray(hero.stats).map((stat) => ({
        label: asString(stat.label, "Milestones"),
        value: asString(stat.value, "0"),
        variant: asString(stat.variant, "default") as "target" | "now" | "default",
      })),
    },
    sections: sections.map((section, index) => ({
      id: asString(section.id, `milestone-${index + 1}`),
      title: asString(section.title, `Milestone ${index + 1}`),
      subtitle: asString(section.subtitle),
      tag_num: asString(section.tag_num, String(index + 1)),
      components: [...preserveStudentComponents(section, `milestone-${index + 1}`)],
    })),
    sidebar: {
      title: asString(sidebar.title, asString(artifact.title, "Learning Roadmap")),
      subtitle: asString(sidebar.subtitle),
      nav: asRecordArray(sidebar.nav).map((item) => ({
        label: asString(item.label),
        href: asString(item.href),
        group: asString(item.group, "a"),
      })),
    },
    accessibility: { language: common(artifact).lang },
  };
}

function readingPassageData(artifact: ArtifactRecord): ReadingPassageData {
  const metadata = asRecord(artifact.metadata);
  const section = asRecord(asRecordArray(artifact.sections)[0]);
  return {
    ...common(artifact),
    passage: asString(section.content),
    questions: asRecordArray(metadata.comprehension_questions).map((question, index) => ({
      id: asString(question.id, `passage-question-${index + 1}`),
      prompt: asString(question.prompt),
      answer: asString(question.answer),
      type: asString(question.type, "short_answer") as "mc" | "short_answer" | "essay",
    })),
    source: asString(metadata.passage_source),
  };
}

function exitTicketData(artifact: ArtifactRecord): ExitTicketData {
  const section = asRecord(asRecordArray(artifact.sections)[0]);
  const questions = asRecordArray(section.components).filter((component) => asString(component.type) === "question_card");
  return {
    ...common(artifact),
    questions: questions.map((question, index) => ({
      id: asString(question.id, `exit-ticket-${index + 1}`),
      prompt: asString(question.text),
      type: "mc" as const,
      options: optionList(question.options),
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

/** Per-child shaping for a Teaching Pack bundle (ADR-056): the same {kind,
 * input} pair the top-level switch below would produce for a standalone
 * export of that artifact type. Types with no generic shaper here (e.g.
 * slide_deck, which renders through a different pipeline) are omitted from
 * the bundle rather than silently mis-rendered as a lesson. */
function childRenderInput(artifact: ArtifactRecord): { kind: string; input: unknown } | null {
  switch (asString(artifact.artifact_type, "lesson")) {
    case "quiz": return { kind: "quiz", input: quizData(artifact) };
    case "worksheet": return { kind: "worksheet", input: worksheetData(artifact) };
    case "drill": return { kind: "drill", input: drillData(artifact) };
    case "recap": return { kind: "recap", input: recapData(artifact) };
    case "infographic": return { kind: "infographic", input: infographicData(artifact) };
    case "roadmap": return { kind: "roadmap", input: roadmapData(artifact) };
    case "reading_passage": return { kind: "reading_passage", input: readingPassageData(artifact) };
    case "exit_ticket": return { kind: "exit_ticket", input: exitTicketData(artifact) };
    case "answer_key": return { kind: "answer_key", input: answerKeyData(artifact) };
    case "lesson": return { kind: "lesson", input: lessonData(artifact) };
    default: return null;
  }
}

async function renderTeachingPackBundle(bundle: ArtifactRecord, lang: string): Promise<string> {
  const rawChildren = Array.isArray(bundle.children) ? bundle.children as unknown[] : [];
  const children = rawChildren
    .map((child) => {
      const c = asRecord(child);
      const childArtifact = ArtifactContentSchema.parse(c.input);
      const shaped = childRenderInput(childArtifact);
      if (!shaped) return null;
      return { id: asString(c.id, shaped.kind), kind: shaped.kind, input: shaped.input };
    })
    .filter((c): c is { id: string; kind: string; input: unknown } => c !== null);
  return render({
    kind: "teaching_pack",
    input: {
      title: asString(bundle.title, "Teaching Pack"),
      subject: asString(bundle.subject, "General"),
      gradeLevel: asString(bundle.gradeLevel, "Grade"),
      children,
    },
    context: makeContext("teacher", lang),
  }).then((r) => r.html);
}

export async function renderAgentArtifact(input: unknown): Promise<string> {
  const rawInput = asRecord(input);
  if (asString(rawInput.artifact_type) === "teaching_pack") {
    return renderTeachingPackBundle(rawInput, asString(asRecord(rawInput.accessibility).language, "vi"));
  }
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
    case "roadmap":
      return render({ kind: "roadmap", input: roadmapData(artifact), context: makeContext("teacher", lang) }).then((r) => r.html);
    case "reading_passage":
      return render({ kind: "reading_passage", input: readingPassageData(artifact), context: makeContext("student", lang) }).then((r) => r.html);
    case "exit_ticket":
      return render({ kind: "exit_ticket", input: exitTicketData(artifact), context: makeContext("student", lang) }).then((r) => r.html);
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
