import { describe, expect, it } from "vitest";
import { renderInverseThinkingHtml } from "../src/inverse-thinking-renderer.js";
import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";

describe("inverse-thinking teacher-only separation", () => {
  it("keeps teacher-only rationale and pack answer out of student HTML", () => {
    const html = renderInverseThinkingHtml(inverseThinkingFixture);

    expect(html).not.toContain("The adverb yesterday conflicts");
    expect(html).not.toContain("She met him last week");
  });

  it("renders teacher-only fields in teacher-only output", () => {
    const html = renderInverseThinkingHtml({ ...inverseThinkingFixture, artifactType: "teacher_only" });

    expect(html).toContain("The adverb yesterday conflicts");
    expect(html).toContain("She met him last week");
  });
});
