import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { getFamily } from "./registry.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CSS_DIR = join(__dirname, "../../src/artifact-ui");

function readCSSFile(relativePath: string): string {
  return readFileSync(join(CSS_DIR, relativePath), "utf-8");
}

// Module-level cache: CSS is a static build artifact — it never changes
// while the process is running. For a 100-cluster batch export (400+ renders),
// this reduces file reads from 1600 to 4. See Issue 016.
const cssCache = new Map<string, string>();

/**
 * Load and concatenate all CSS for a given Artifact UI family.
 *
 * Load order: contract.css → family tokens → primitives.css → family components.
 * All four are inlined into a single <style> block by the Eta template.
 * Result is memoized for the lifetime of the process.
 */
export function loadArtifactCSS(familyId: string): string {
  const cached = cssCache.get(familyId);
  if (cached !== undefined) return cached;

  const family = getFamily(familyId); // throws descriptive error if unknown
  const css = [
    readCSSFile("tokens/contract.css"),
    readCSSFile(family.tokenFile),
    readCSSFile("primitives.css"),
    readCSSFile(family.familyFile),
  ].join("\n\n");

  cssCache.set(familyId, css);
  return css;
}

/** Clear the CSS cache. For testing only — production code never calls this. */
export function clearArtifactCSSCache(): void {
  cssCache.clear();
}
