import { describe, expect, it } from "vitest";
import { renderInverseThinkingHtml } from "../src/inverse-thinking-renderer.js";
import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";

describe("renderInverseThinkingHtml", () => {
  for (const artifactType of ["lesson", "worksheet", "quiz", "drill"] as const) {
    it(`renders standalone ${artifactType} HTML`, () => {
      const html = renderInverseThinkingHtml({ ...inverseThinkingFixture, artifactType });

      expect(html).toContain("<!DOCTYPE html>");
      expect(html).toContain("oh-my-class");
      expect(html).toContain('name="viewport"');
      expect(html).toContain("@media print");
      expect(html).not.toMatch(/https?:\/\//);
      expect(html).not.toMatch(/<link\s/i);
      expect(html).not.toMatch(/<script\s/i);
      expect(html).toContain("case-file");
      expect(html.toLowerCase()).toContain("summary table");
    });
  }
});
