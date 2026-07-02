import { loadArtifactCSS } from "../artifact-ui/loader.js";
import { loadTheme } from "../theme/loader.js";
import type { RenderContext } from "./types.js";

export type ThemeResolveRequest = {
  readonly themeId: string;
  readonly familyId?: string;
  readonly renderMode: RenderContext["renderMode"];
  readonly locale: RenderContext["locale"];
};

export type ResolvedTheme = {
  readonly css: string;
  readonly cacheKey: string;
};

export class ThemeResolver {
  readonly #cache = new Map<string, ResolvedTheme>();

  resolve(request: ThemeResolveRequest): ResolvedTheme {
    const cacheKey = [request.themeId, request.familyId ?? "regular", request.renderMode, request.locale].join(":");
    const cached = this.#cache.get(cacheKey);
    if (cached) return cached;

    const baseCss = loadTheme(request.themeId);
    const familyCss = request.familyId ? loadArtifactCSS(request.familyId) : "";
    const resolved = { css: familyCss ? `${baseCss}\n${familyCss}` : baseCss, cacheKey };
    this.#cache.set(cacheKey, resolved);
    return resolved;
  }
}

export const defaultThemeResolver = new ThemeResolver();
