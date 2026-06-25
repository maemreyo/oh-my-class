/**
 * Answer key artifact data contract.
 *
 * Mirrors AnswerKeyContent Python Pydantic model (common/contracts/answer_key.py).
 * Used when artifact_type == "answer_key".
 * Teacher-only view — answers always visible.
 */

import type { ContentComponent } from "./components.js";

export interface AnswerKeySection {
  id: string;
  title: string;
  sub?: string;
  range?: string;
  group?: string;
  instruction?: string;
  summary?: string;
  components?: ContentComponent[];
}

export interface AnswerKeyMetadata {
  total_questions?: number;
  groups?: Record<string, { label: string; color?: string }>;
}

export interface AnswerKeyData {
  title: string;
  theme?: string;
  sections?: AnswerKeySection[];
  metadata?: AnswerKeyMetadata;
  accessibility?: { language?: string };
}
