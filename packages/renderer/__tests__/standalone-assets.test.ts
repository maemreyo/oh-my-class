import { describe, expect, it } from "vitest";
import { renderInverseThinkingHtml } from "../src/inverse-thinking-renderer.js";
import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";

describe("standalone inverse-thinking assets", () => {
  it("contains no external assets, Google Fonts, or CDN references", async () => {
    const html = await renderInverseThinkingHtml(inverseThinkingFixture);

    expect(html).not.toMatch(/https?:\/\//i);
    expect(html).not.toMatch(/fonts\.googleapis|google fonts|cdn/i);
    expect(html).not.toMatch(/<link\s/i);
    expect(html).not.toMatch(/@import/i);
  });
});
