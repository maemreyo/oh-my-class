import { fixturePlugin } from "../plugins/fixture.js";
import { quizPlugin } from "../plugins/quiz.js";
import { worksheetPlugin } from "../plugins/worksheet.js";
import { drillPlugin } from "../plugins/drill.js";
import { createPluginRegistry } from "./registry.js";

export const defaultRegistry = createPluginRegistry([fixturePlugin, quizPlugin, worksheetPlugin, drillPlugin]);

export function rendererPluginMetadata() {
  return defaultRegistry.metadata();
}
