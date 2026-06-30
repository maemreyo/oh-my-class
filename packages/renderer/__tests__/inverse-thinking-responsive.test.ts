import { describe, expect, it } from "vitest";
import { renderInverseThinkingHtml } from "../src/inverse-thinking-renderer.js";
import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";

describe("inverse-thinking responsive and print structure", () => {
  it("contains mobile, overflow, and print-safe layout hooks", () => {
    const html = renderInverseThinkingHtml(inverseThinkingFixture);

    expect(html).toContain("@media(max-width:480px)");
    expect(html).toContain("table-scroll");
    expect(html).toContain("overflow-x:auto");
    expect(html).toContain("page-break-inside:avoid");
  });
});
