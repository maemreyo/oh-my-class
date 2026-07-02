import { RendererError, RendererErrorCategory, RendererErrorCode } from "./errors.js";

const externalAssetPatterns = [
  /\s(?:src|href)=["']https?:\/\//i,
  /url\(["']?https?:\/\//i,
  /@import\s+url\(["']?https?:\/\//i,
] as const;

export function enforceInlineOnlyAssetPolicy(html: string): void {
  const matchedPattern = externalAssetPatterns.find((pattern) => pattern.test(html));
  if (!matchedPattern) return;
  throw new RendererError({
    code: RendererErrorCode.ExternalAsset,
    category: RendererErrorCategory.Policy,
    message: "Rendered HTML contains an external asset reference.",
    details: { policy: "inline-only", pattern: matchedPattern.source },
  });
}
