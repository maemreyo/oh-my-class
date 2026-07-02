import { createHash } from "node:crypto";

import { eta } from "../eta-engine.js";
import { enforceInlineOnlyAssetPolicy } from "./asset-policy.js";
import { RendererError, RendererErrorCategory, RendererErrorCode } from "./errors.js";
import { loadManagedScripts } from "./managed-scripts.js";
import { defaultRegistry } from "./runtime.js";
import { sanitizeRenderedHtml } from "./sanitizer.js";
import { defaultThemeResolver, type ThemeResolver } from "./theme-resolver.js";
import type { PluginRegistry } from "./registry.js";
import type { RenderBatchRequest, RenderRequest, RenderResponse } from "./types.js";

const isoTimestampPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;

type RenderOptions = {
  readonly registry?: PluginRegistry;
  readonly themeResolver?: ThemeResolver;
};

export async function render(request: RenderRequest, options: RenderOptions = {}): Promise<RenderResponse> {
  const startedAt = performance.now();
  const registry = options.registry ?? defaultRegistry;
  const themeResolver = options.themeResolver ?? defaultThemeResolver;
  const plugin = registry.get(request.kind);

  if (!plugin.audience.supported.includes(request.context.audience)) {
    throw new RendererError({
      code: RendererErrorCode.UnsupportedAudience,
      category: RendererErrorCategory.Policy,
      message: `Renderer plugin ${request.kind} does not support audience ${request.context.audience}.`,
      details: { kind: request.kind, audience: request.context.audience },
    });
  }

  const parsed = plugin.schema.safeParse(request.input);
  if (!parsed.success) {
    throw new RendererError({
      code: RendererErrorCode.ValidationFailed,
      category: RendererErrorCategory.Validation,
      message: `Renderer input validation failed for kind ${request.kind}.`,
      details: { issues: parsed.error.issues },
    });
  }

  const theme = themeResolver.resolve({
    themeId: request.context.theme,
    familyId: plugin.familyId,
    renderMode: request.context.renderMode,
    locale: request.context.locale,
  });
  const managedScripts = loadManagedScripts(plugin.managedScripts);
  const templateData = await plugin.adapt(parsed.data, request.context, { themeCss: theme.css, managedScripts });
  const rawHtml = await eta.renderAsync(plugin.templatePath(request.context), templateData);
  if (rawHtml === undefined) {
    throw new RendererError({
      code: RendererErrorCode.TemplateMissing,
      category: RendererErrorCategory.Template,
      message: `Renderer template not found for kind ${request.kind}.`,
      details: { kind: request.kind, templatePath: plugin.templatePath(request.context) },
    });
  }

  enforceInlineOnlyAssetPolicy(rawHtml, plugin.managedScripts);
  const html = sanitizeRenderedHtml(rawHtml, plugin.sanitizerPolicy);
  enforceInlineOnlyAssetPolicy(html, plugin.managedScripts);
  const renderedAt = new Date().toISOString();
  if (!isoTimestampPattern.test(renderedAt)) {
    throw new RendererError({
      code: RendererErrorCode.ValidationFailed,
      category: RendererErrorCategory.Validation,
      message: "Renderer timestamp generation produced an invalid ISO timestamp.",
      details: { renderedAt },
    });
  }

  return {
    html,
    manifest: {
      kind: plugin.kind,
      rendererVersion: request.context.versions.rendererVersion,
      pluginVersion: plugin.version,
      templateVersion: plugin.templateVersion,
      themeVersion: plugin.themeVersion,
      sanitizerPolicyVersion: plugin.sanitizerPolicy.version,
      renderedAt,
      contentHash: createHash("sha256").update(html).digest("hex"),
    },
    diagnostics: [],
    metrics: { renderTimeMs: Math.max(0, performance.now() - startedAt) },
  };
}

export async function renderBatch(request: RenderBatchRequest, options: RenderOptions = {}): Promise<readonly RenderResponse[]> {
  return Promise.all(request.requests.map((item) => render(item, options)));
}
