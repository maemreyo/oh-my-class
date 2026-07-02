import { describe, expect, it } from "vitest";
import { renderInverseThinkingHtml } from "../src/inverse-thinking-renderer.js";
import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";

describe("inverse-thinking HTML structure", () => {
  it("contains valid HTML5 structure with viewport meta", async () => {
    const html = await renderInverseThinkingHtml(inverseThinkingFixture);

    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain('<meta name="viewport"');
    expect(html).toContain("<head>");
    expect(html).toContain("</head>");
    expect(html).toContain("<body");
    expect(html).toContain("</body>");
  });

  it("contains art-table-wrap for summary table (overflow-safe on mobile)", async () => {
    const html = await renderInverseThinkingHtml(inverseThinkingFixture);
    expect(html).toContain("art-table-wrap");
  });

  it("CSS inlined in <style> block (no external stylesheets)", async () => {
    const html = await renderInverseThinkingHtml(inverseThinkingFixture);
    expect(html).toContain("<style>");
    expect(html).not.toMatch(/<link\s/i);
    expect(html).not.toMatch(/@import/i);
  });
});
