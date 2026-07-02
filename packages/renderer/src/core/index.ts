export { RendererError, RendererErrorCategory, RendererErrorCode } from "./errors.js";
export { PluginRegistry, createPluginRegistry } from "./registry.js";
export { render, renderBatch } from "./render.js";
export { rendererPluginMetadata } from "./runtime.js";
export { ThemeResolver, defaultThemeResolver } from "./theme-resolver.js";
export { sanitizeRenderedHtml } from "./sanitizer.js";
export { enforceInlineOnlyAssetPolicy } from "./asset-policy.js";
export { hashManagedScriptSource, loadManagedScripts } from "./managed-scripts.js";
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
} from "./types.js";
