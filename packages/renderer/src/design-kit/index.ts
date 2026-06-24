import { extractCSSVars } from "./extractor.js";
import { mapToSemanticTokens } from "./mapper.js";
import { llmExtractTokens } from "./llm-extractor.js";
import { proposeThemeJSON } from "./proposer.js";
import { validateThemeTokens } from "./validator.js";
import type { ThemeTokens } from "../theme/tokens.js";

export type { CSSVar } from "./extractor.js";
export type { ValidationResult } from "./validator.js";

export interface ImportResult {
  method: "regex" | "llm";
  tokens: ThemeTokens;
  confidence: number;  // 0.0–1.0: % of semantic fields successfully extracted
  warnings: string[];  // fields that fell back to defaults
}

const MIN_VARS_FOR_REGEX = 3;
const TOTAL_SEMANTIC_FIELDS = 10;

export async function importDesignKit(
  html: string,
  options: {
    name?: string;
    llmClient?: { chat: (opts: unknown) => Promise<{ content: string }> };
  } = {},
): Promise<ImportResult> {
  const name = options.name ?? "custom";
  let method: "regex" | "llm" = "regex";
  let extracted: Partial<ThemeTokens["semantic"]>;

  const vars = extractCSSVars(html);
  const partial = mapToSemanticTokens(vars);
  const extractedCount = Object.keys(partial).length;

  if (extractedCount < MIN_VARS_FOR_REGEX && options.llmClient) {
    method = "llm";
    extracted = await llmExtractTokens(html, options.llmClient);
  } else {
    extracted = partial;
  }

  const tokens = proposeThemeJSON(extracted, name);
  const validation = validateThemeTokens(tokens);

  const filledCount = Object.keys(extracted).length;
  const confidence = Math.min(filledCount / TOTAL_SEMANTIC_FIELDS, 1.0);

  const warnings = validation.missing.map(
    (field) => `${field} not found in source HTML — using default value`,
  );

  return { method, tokens, confidence, warnings };
}
