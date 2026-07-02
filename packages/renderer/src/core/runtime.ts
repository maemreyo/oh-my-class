import { fixturePlugin } from "../plugins/fixture.js";
import { createPluginRegistry } from "./registry.js";

export const defaultRegistry = createPluginRegistry([fixturePlugin]);

export function rendererPluginMetadata() {
  return defaultRegistry.metadata();
}
