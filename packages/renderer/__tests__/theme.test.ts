import { describe, expect, it, beforeEach } from "vitest";
import { ThemeCSSGenerator } from "../src/theme/generator.js";
import { loadTheme, clearThemeCache } from "../src/theme/loader.js";
import type { ThemeTokens } from "../src/theme/tokens.js";

const minimalTokens: ThemeTokens = {
  name: "test",
  primitives: {
    colorPalette: {},
    spacing: {},
    fontFamilyHeading: "serif",
    fontFamilyBody: "sans-serif",
    fontFamilyMono: "monospace",
    fontSizeScale: {},
    fontWeightScale: {},
    borderRadius: {},
    shadow: {},
  },
  semantic: {
    colorBg: "#fff",
    colorBgCard: "#fff",
    colorBgDeep: "#eee",
    colorText: "#000",
    colorTextSoft: "#666",
    colorTextFaint: "#999",
    colorBorder: "#ccc",
    colorBorderSoft: "#ddd",
    colorAccent: "#f00",
    colorAccentDeep: "#c00",
    colorAccentTint: "rgba(255,0,0,0.1)",
    colorSuccess: "#0f0",
    colorWarning: "#fa0",
    colorError: "#f00",
    categoryColors: {},
  },
};

describe("ThemeCSSGenerator", () => {
  it("produces --color-bg CSS var", () => {
    const gen = new ThemeCSSGenerator();
    const css = gen.generate(minimalTokens);
    expect(css).toContain("--color-bg: #fff;");
  });

  it("produces --font-heading CSS var", () => {
    const gen = new ThemeCSSGenerator();
    const css = gen.generate(minimalTokens);
    expect(css).toContain("--font-heading: serif;");
  });

  it("produces --font-body CSS var", () => {
    const gen = new ThemeCSSGenerator();
    const css = gen.generate(minimalTokens);
    expect(css).toContain("--font-body: sans-serif;");
  });

  it("maps category colors", () => {
    const tokens: ThemeTokens = {
      ...minimalTokens,
      semantic: {
        ...minimalTokens.semantic,
        categoryColors: {
          a: { base: "#33508F", tint: "rgba(51,80,143,0.08)" },
        },
      },
    };
    const css = new ThemeCSSGenerator().generate(tokens);
    expect(css).toContain("--color-category-a: #33508F;");
    expect(css).toContain("--color-category-a-tint: rgba(51,80,143,0.08);");
  });

  it("includes optional component tokens when present", () => {
    const tokens: ThemeTokens = {
      ...minimalTokens,
      component: { questionCardRadius: "8px", flashcardHeight: "220px" },
    };
    const css = new ThemeCSSGenerator().generate(tokens);
    expect(css).toContain("--question-card-radius: 8px;");
    expect(css).toContain("--flashcard-height: 220px;");
  });

  it("omits component tokens when component is absent", () => {
    const css = new ThemeCSSGenerator().generate(minimalTokens);
    expect(css).not.toContain("--question-card-radius");
  });

  it("includes all 14 semantic color vars", () => {
    const css = new ThemeCSSGenerator().generate(minimalTokens);
    const expectedVars = [
      "--color-bg", "--color-bg-card", "--color-bg-deep",
      "--color-text", "--color-text-soft", "--color-text-faint",
      "--color-border", "--color-border-soft",
      "--color-accent", "--color-accent-deep", "--color-accent-tint",
      "--color-success", "--color-warning", "--color-error",
    ];
    for (const v of expectedVars) {
      expect(css).toContain(v);
    }
  });
});

describe("loadTheme", () => {
  beforeEach(() => clearThemeCache());

  it("returns CSS string for default theme", () => {
    const css = loadTheme("default");
    expect(typeof css).toBe("string");
    expect(css).toContain("--color-bg:");
  });

  it("default theme has correct paper color", () => {
    const css = loadTheme("default");
    expect(css).toContain("--color-bg: #FBF4F0;");
  });

  it("default theme has correct accent (red)", () => {
    const css = loadTheme("default");
    expect(css).toContain("--color-accent: #B23A2E;");
  });

  it("falls back to default for unknown theme name", () => {
    const css = loadTheme("nonexistent-theme-xyz");
    expect(css).toContain("--color-bg:");
  });

  it("caches result — same name returns same string reference", () => {
    const first = loadTheme("default");
    const second = loadTheme("default");
    expect(first).toBe(second);
  });

  it("clearThemeCache breaks the cache", () => {
    const first = loadTheme("default");
    clearThemeCache();
    const second = loadTheme("default");
    expect(second).toEqual(first); // same content
  });

  it("returns CSS string for forest theme", () => {
    const css = loadTheme("forest");
    expect(css).toContain("--color-bg:");
    expect(css).toContain("--color-accent:");
  });

  it("returns CSS string for ocean theme", () => {
    const css = loadTheme("ocean");
    expect(css).toContain("--color-bg:");
    expect(css).toContain("--color-accent:");
  });

  it("returns high-contrast dyslexia-friendly CSS with offline fonts", () => {
    const css = loadTheme("high-contrast-dyslexia");
    expect(css).toContain("--color-bg: #FFFDF2;");
    expect(css).toContain("--color-text: #111111;");
    expect(css).toContain("Atkinson Hyperlegible");
    expect(css).not.toMatch(/https?:\/\//);
  });

  it("default theme includes category colors a–e", () => {
    const css = loadTheme("default");
    for (const letter of ["a", "b", "c", "d", "e"]) {
      expect(css).toContain(`--color-category-${letter}:`);
    }
  });
});
