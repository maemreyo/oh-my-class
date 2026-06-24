/**
 * Singleton Eta instance — file-based template rendering.
 *
 * M2 decision: templates live in `../templates/`, rendered via
 * `eta.renderAsync('pages/quiz', data)`. All data accessed via `it.` —
 * `useWith: false` prevents scope pollution.
 *
 * XSS layer 1: `autoEscape: true` escapes HTML entities in `<%= %>` expressions.
 */

import { Eta } from "eta";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const eta = new Eta({
  views: path.resolve(__dirname, "../templates"),
  defaultExtension: ".html",
  cache: process.env.NODE_ENV === "production",
  autoEscape: true,
  useWith: false,
});
