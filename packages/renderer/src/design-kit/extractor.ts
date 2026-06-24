/**
 * Pure regex extraction of CSS custom properties from :root {} blocks.
 * No LLM, no DOM — works on any HTML string.
 */

export interface CSSVar {
  name: string;   // e.g. "--paper"
  value: string;  // e.g. "#FBF4F0"
  source: string; // the :root rule it was found in (truncated)
}

// Matches :root { ... } blocks (handles multiline)
const ROOT_BLOCK_RE = /:root\s*\{([^}]+)\}/gs;

// Matches --var-name: value; pairs
const CSS_VAR_RE = /--([a-zA-Z0-9-]+)\s*:\s*([^;]+);/g;

export function extractCSSVars(html: string): CSSVar[] {
  const vars: CSSVar[] = [];
  let rootMatch: RegExpExecArray | null;

  ROOT_BLOCK_RE.lastIndex = 0;
  while ((rootMatch = ROOT_BLOCK_RE.exec(html)) !== null) {
    const block = rootMatch[1];
    CSS_VAR_RE.lastIndex = 0;
    let varMatch: RegExpExecArray | null;

    while ((varMatch = CSS_VAR_RE.exec(block)) !== null) {
      vars.push({
        name: `--${varMatch[1]}`,
        value: varMatch[2].trim(),
        source: rootMatch[0].slice(0, 30) + "...",
      });
    }
  }

  return vars;
}
