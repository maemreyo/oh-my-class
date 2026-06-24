import { buildSandboxAttribute } from "./csp.js";
import type { ArtifactType } from "../contracts/index.js";

/**
 * Returns HTML for embedding the preview iframe in the teacher dashboard.
 * Includes correct sandbox attribute — never combines allow-scripts + allow-same-origin.
 */
export function buildIframeEmbed(runId: string, type: ArtifactType): string {
  const sandbox = buildSandboxAttribute(type);
  const src = `/api/preview/${runId}`;

  return `<iframe
  src="${src}"
  sandbox="${sandbox}"
  title="Artifact preview"
  class="artifact-preview-frame"
  loading="lazy"
  style="width:100%; height:100%; border:none; border-radius:var(--radius-md)"
  aria-label="Preview of generated artifact"
></iframe>`;
}
