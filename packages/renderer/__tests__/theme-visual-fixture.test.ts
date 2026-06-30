import { describe, expect, it } from "vitest";
import { renderInverseThinkingHtml } from "../src/inverse-thinking-renderer.js";
import { loadTheme } from "../src/theme/index.js";
import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";

const themes = ["default", "ocean", "forest"] as const;

describe("theme visual fixture", () => {
  for (const theme of themes) {
    it(`renders inverse-thinking artifact with ${theme} theme tokens and no external assets`, () => {
      const themeCss = loadTheme(theme);
      const artifactHtml = renderInverseThinkingHtml(inverseThinkingFixture);
      const html = artifactHtml.replace("</head>", `<style>${themeCss}</style></head>`);

      expect(html).toContain("<!DOCTYPE html>");
      expect(html).toContain("oh-my-class");
      expect(themeCss).toContain("--color-bg:");
      expect(themeCss).toContain("--color-accent:");
      expect(html).not.toMatch(/https?:\/\//i);
      expect(html).not.toMatch(/<link\s/i);
    });
  }
});
