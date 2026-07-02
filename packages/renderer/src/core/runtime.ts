import { fixturePlugin } from "../plugins/fixture.js";
import { quizPlugin } from "../plugins/quiz.js";
import { worksheetPlugin } from "../plugins/worksheet.js";
import { drillPlugin } from "../plugins/drill.js";
import { recapPlugin } from "../plugins/recap.js";
import { infographicPlugin } from "../plugins/infographic.js";
import { lessonPlugin } from "../plugins/lesson.js";
import { answerKeyPlugin } from "../plugins/answer-key.js";
import { createPluginRegistry } from "./registry.js";

export const defaultRegistry = createPluginRegistry([fixturePlugin, quizPlugin, worksheetPlugin, drillPlugin, recapPlugin, infographicPlugin, lessonPlugin, answerKeyPlugin]);

export function rendererPluginMetadata() {
  return defaultRegistry.metadata();
}
