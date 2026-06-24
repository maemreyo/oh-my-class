import sanitizeHtmlLib from "sanitize-html";
import type { IOptions } from "sanitize-html";
import type { ArtifactType } from "../contracts/index.js";
import { BASE_CONFIG } from "./base-config.js";
import { QUIZ_CONFIG } from "./configs/quiz.js";
import { DRILL_CONFIG } from "./configs/drill.js";
import { WORKSHEET_CONFIG } from "./configs/worksheet.js";
import { RECAP_CONFIG } from "./configs/recap.js";
import { INFOGRAPHIC_CONFIG } from "./configs/infographic.js";
import { LESSON_CONFIG } from "./configs/lesson.js";
import { ANSWER_KEY_CONFIG } from "./configs/answer_key.js";
import { FLASHCARD_DECK_CONFIG } from "./configs/flashcard_deck.js";
import { READING_PASSAGE_CONFIG } from "./configs/reading_passage.js";
import { EXIT_TICKET_CONFIG } from "./configs/exit_ticket.js";

const CONFIG_MAP: Record<ArtifactType, IOptions> = {
  lesson:          LESSON_CONFIG,
  quiz:            QUIZ_CONFIG,
  drill:           DRILL_CONFIG,
  worksheet:       WORKSHEET_CONFIG,
  recap:           RECAP_CONFIG,
  infographic:     INFOGRAPHIC_CONFIG,
  answer_key:      ANSWER_KEY_CONFIG,
  flashcard_deck:  FLASHCARD_DECK_CONFIG,
  reading_passage: READING_PASSAGE_CONFIG,
  exit_ticket:     EXIT_TICKET_CONFIG,
  teaching_pack:   BASE_CONFIG,   // teaching_pack is a bundle — sanitize each artifact independently
};

/**
 * Server-side HTML sanitization with per-artifact-type allowlists.
 * Uses sanitize-html (no DOM required).
 *
 * For full HTML documents: only the <body> content is sanitized.
 * The document shell (<html>, <head>, theme CSS) comes from trusted templates.
 * For HTML fragments: the entire string is sanitized.
 */
export function sanitize(html: string, type: ArtifactType): string {
  const config = CONFIG_MAP[type] ?? BASE_CONFIG;

  // Full document: extract body, sanitize only its content, reassemble
  const bodyMatch = html.match(/(<body[^>]*>)([\s\S]*)(<\/body>)/i);
  if (bodyMatch) {
    const sanitizedBody = sanitizeHtmlLib(bodyMatch[2], config);
    return html.replace(bodyMatch[0], `${bodyMatch[1]}${sanitizedBody}${bodyMatch[3]}`);
  }

  // Fragment: sanitize the whole string, preserving DOCTYPE if present
  const doctypeMatch = html.match(/^(<!DOCTYPE[^>]*>)\s*/i);
  const doctype = doctypeMatch ? doctypeMatch[1] : "";
  const body = doctypeMatch ? html.slice(doctypeMatch[0].length) : html;
  const sanitized = sanitizeHtmlLib(body, config);
  return doctype ? `${doctype}\n${sanitized}` : sanitized;
}
