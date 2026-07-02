import { describe, expect, it } from "vitest";
import { renderInverseThinkingHtml } from "../src/inverse-thinking-renderer.js";
import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";

describe("renderInverseThinkingHtml", () => {
  for (const artifactType of ["lesson", "worksheet", "quiz", "drill"] as const) {
    it(`renders standalone ${artifactType} HTML with investigation-folder theme`, async () => {
      const html = await renderInverseThinkingHtml({ ...inverseThinkingFixture, artifactType });

      expect(html).toContain("<!DOCTYPE html>");
      expect(html).toContain("oh-my-class");
      expect(html).toContain('name="viewport"');
      expect(html).not.toMatch(/https?:\/\//);
      expect(html).not.toMatch(/<link\s/i);
      expect(html).toContain('data-artifact-theme="investigation-folder"');
      expect(html).toContain("art-case");
      // Summary table section is present
      expect(html).toContain("art-table-wrap");
    });
  }
});
