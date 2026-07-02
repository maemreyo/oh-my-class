import { fixturePlugin } from "../plugins/fixture.js";
import { quizPlugin } from "../plugins/quiz.js";
import { worksheetPlugin } from "../plugins/worksheet.js";
import { drillPlugin } from "../plugins/drill.js";
import { recapPlugin } from "../plugins/recap.js";
import { infographicPlugin } from "../plugins/infographic.js";
import { lessonPlugin } from "../plugins/lesson.js";
import { answerKeyPlugin } from "../plugins/answer-key.js";
import { flashcardDeckPlugin } from "../plugins/flashcard-deck.js";
import { readingPassagePlugin } from "../plugins/reading-passage.js";
import { exitTicketPlugin } from "../plugins/exit-ticket.js";
import { roadmapPlugin } from "../plugins/roadmap.js";
import { teachingPackPlugin } from "../plugins/teaching-pack.js";
import { createPluginRegistry } from "./registry.js";

export const defaultRegistry = createPluginRegistry([
  fixturePlugin,
  quizPlugin,
  worksheetPlugin,
  drillPlugin,
  recapPlugin,
  infographicPlugin,
  lessonPlugin,
  answerKeyPlugin,
  flashcardDeckPlugin,
  readingPassagePlugin,
  exitTicketPlugin,
  roadmapPlugin,
  teachingPackPlugin,
]);

export function rendererPluginMetadata() {
  return defaultRegistry.metadata();
}
