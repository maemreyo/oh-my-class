import { hashManagedScriptSource } from "./managed-scripts.js";
import { RendererError, RendererErrorCategory, RendererErrorCode } from "./errors.js";
import type { ManagedScriptDeclaration } from "./types.js";

const externalAssetPatterns = [
  /\s(?:src|href)=["']https?:\/\//i,
  /<link\b[^>]*\brel=["']stylesheet["'][^>]*>/i,
  /url\(["']?https?:\/\//i,
  /@import\s+url\(["']?https?:\/\//i,
  /@font-face\b[\s\S]*?url\(["']?https?:\/\//i,
] as const;

const scriptBlockPattern = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;

function managedScriptId(attributes: string): string | undefined {
  const match = attributes.match(/\bdata-managed-script-id=["']([^"']+)["']/i);
  return match?.[1];
}

function assertManagedInlineScripts(html: string, declarations: readonly ManagedScriptDeclaration[]): void {
  for (const match of html.matchAll(scriptBlockPattern)) {
    const attributes = match[1] ?? "";
    if (/\bsrc=["']/i.test(attributes)) {
      throw new RendererError({
        code: RendererErrorCode.ExternalAsset,
        category: RendererErrorCategory.Policy,
        message: "Rendered HTML contains an unmanaged external script.",
        details: { policy: "inline-only" },
      });
    }
    const id = managedScriptId(attributes);
    const source = match[2] ?? "";
    const declaration = declarations.find((candidate) => candidate.id === id);
    if (!id || !declaration || hashManagedScriptSource(source) !== declaration.sha256) {
      throw new RendererError({
        code: RendererErrorCode.ExternalAsset,
        category: RendererErrorCategory.Policy,
        message: "Rendered HTML contains an unmanaged inline script.",
        details: { policy: "inline-only", id },
      });
    }
  }
}

export function enforceInlineOnlyAssetPolicy(html: string, declarations: readonly ManagedScriptDeclaration[] = []): void {
  const matchedPattern = externalAssetPatterns.find((pattern) => pattern.test(html));
  if (matchedPattern) {
    throw new RendererError({
      code: RendererErrorCode.ExternalAsset,
      category: RendererErrorCategory.Policy,
      message: "Rendered HTML contains an external asset reference.",
      details: { policy: "inline-only", pattern: matchedPattern.source },
    });
  }
  assertManagedInlineScripts(html, declarations);
}
