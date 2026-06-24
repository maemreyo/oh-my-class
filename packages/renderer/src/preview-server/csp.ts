import type { ArtifactType } from "../contracts/index.js";

const STATIC_TYPES = new Set<ArtifactType>([
  "lesson", "recap", "infographic", "answer_key", "reading_passage", "exit_ticket",
]);

const INTERACTIVE_TYPES = new Set<ArtifactType>([
  "quiz", "drill", "worksheet", "flashcard_deck",
]);

/**
 * Build Content-Security-Policy header value for artifact type.
 * All types: no external resources (standalone HTML contract).
 * Interactive types: allow inline scripts for quiz/flip functionality.
 * Static types: no scripts for maximum safety.
 */
export function buildCSPHeader(type: ArtifactType): string {
  const isInteractive = INTERACTIVE_TYPES.has(type);

  const directives = [
    "default-src 'none'",
    "style-src 'unsafe-inline'",
    isInteractive ? "script-src 'unsafe-inline'" : "script-src 'none'",
    "img-src data:",
    "font-src 'none'",
    "connect-src 'none'",
    "frame-src 'none'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
  ];

  return directives.join("; ");
}

/**
 * Build iframe sandbox attribute value.
 * Critical: NEVER combine allow-scripts + allow-same-origin.
 * Static types: no scripts in sandbox (consistent with CSP script-src 'none').
 * Interactive types: allow-scripts allow-forms (no allow-same-origin — prevents parent DOM access).
 */
export function buildSandboxAttribute(type: ArtifactType): string {
  const isInteractive = INTERACTIVE_TYPES.has(type);
  if (isInteractive) {
    return "allow-scripts allow-forms";
  }
  return "";
}
