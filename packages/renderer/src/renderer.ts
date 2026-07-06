/**
 * Core renderer — takes typed artifact data and produces standalone HTML.
 *
 * R2 decision: `renderArtifact<T>()` is the stable public API.
 * Internals rewired from manual HTML generation to `eta.renderAsync()`.
 *
 * All output is self-contained: theme CSS inlined, no CDN, no external assets.
 */

import { eta } from "./eta-engine.js";
import type { ArtifactDataMap, ArtifactType } from "./contracts/index.js";
import { loadTheme } from "./theme/loader.js";
import { sanitize } from "./sanitizer/index.js";
import { assertStudentSlideDeckHtmlIsSafe, projectSlideDeckSurface } from "./slide-deck-projection.js";

export type { ArtifactDataMap, ArtifactType } from "./contracts/index.js";
export {
  PluginRegistry,
  RendererError,
  RendererErrorCategory,
  RendererErrorCode,
  ThemeResolver,
  createPluginRegistry,
  defaultThemeResolver,
  enforceInlineOnlyAssetPolicy,
  hashManagedScriptSource,
  loadManagedScripts,
  render,
  renderBatch,
  rendererPluginMetadata,
  sanitizeRenderedHtml,
} from "./core/index.js";
export type {
  ArtifactKindCapabilities,
  ArtifactKindPlugin,
  AudiencePolicy,
  PluginMetadata,
  RenderAssetPolicy,
  RenderAudience,
  RenderBatchRequest,
  RenderContext,
  RenderDiagnostic,
  RenderLocale,
  ManagedScript,
  ManagedScriptDeclaration,
  RenderManifest,
  RenderMetrics,
  RenderMode,
  RenderRequest,
  RenderResponse,
  RenderServices,
  RenderVersionContext,
  SanitizerPolicy,
} from "./core/index.js";

/**
 * Render typed artifact data to a sanitized, standalone HTML string.
 *
 * Uses Eta file-based templates: `pages/{type}.html` included in `base.html`.
 * Theme CSS is loaded at runtime and injected into the base template.
 *
 * @example
 * ```ts
 * const html = await renderArtifact('quiz', {
 *   title: 'Test Quiz',
 *   subject: 'English',
 *   gradeLevel: 'Grade 8',
 *   questions: [{ id: 'q1', prompt: '2+2?', options: [{label:'A',text:'3'},{label:'B',text:'4'}], answer: 'B' }],
 * })
 * ```
 */
export async function renderArtifact<T extends ArtifactType>(
  type: T,
  data: ArtifactDataMap[T],
): Promise<string> {
  const themeName = (data as { theme?: string }).theme ?? "default";
  const lang = (data as { lang?: string }).lang ?? "vi";
  const themeCSS = loadTheme(themeName);
  const templateData = type === "slide_deck" ? projectSlideDeckSurface(data as ArtifactDataMap["slide_deck"]) : data;

  const html = await eta.renderAsync(`pages/${type}`, {
    ...templateData,
    themeCSS,
    lang,
  });

  const sanitized = sanitize(html, type);
  if (type === "slide_deck") assertStudentSlideDeckHtmlIsSafe(templateData as ReturnType<typeof projectSlideDeckSurface>, sanitized);
  return sanitized;
}


/**
 * Render an Eta template string with data (convenience helper).
 */
export function renderTemplate(
  templateStr: string,
  data: Record<string, unknown>,
): string {
  if (!templateStr) return "";
  const result = eta.renderString(templateStr, data);
  return result ?? "";
}
