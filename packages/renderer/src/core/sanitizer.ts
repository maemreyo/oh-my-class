import sanitizeHtmlLib from "sanitize-html";
import type { IOptions } from "sanitize-html";

import { BASE_CONFIG } from "../sanitizer/base-config.js";
import type { SanitizerPolicy } from "./types.js";

type FullDocumentParts = {
  readonly bodyMatch: RegExpMatchArray;
};

function fullDocumentParts(html: string): FullDocumentParts | undefined {
  const bodyMatch = html.match(/(<body[^>]*>)([\s\S]*)(<\/body>)/i);
  return bodyMatch ? { bodyMatch } : undefined;
}

function configFor(_policy: SanitizerPolicy): IOptions {
  return BASE_CONFIG;
}

export function sanitizeRenderedHtml(html: string, policy: SanitizerPolicy): string {
  const config = configFor(policy);
  const documentParts = fullDocumentParts(html);
  if (documentParts) {
    const [, bodyOpen, bodyContent, bodyClose] = documentParts.bodyMatch;
    const sanitizedBody = sanitizeHtmlLib(bodyContent ?? "", config);
    return html.replace(documentParts.bodyMatch[0], `${bodyOpen ?? "<body>"}${sanitizedBody}${bodyClose ?? "</body>"}`);
  }

  const doctypeMatch = html.match(/^(<!DOCTYPE[^>]*>)\s*/i);
  const doctype = doctypeMatch?.[1] ?? "";
  const body = doctypeMatch ? html.slice(doctypeMatch[0].length) : html;
  const sanitized = sanitizeHtmlLib(body, config);
  return doctype ? `${doctype}\n${sanitized}` : sanitized;
}
