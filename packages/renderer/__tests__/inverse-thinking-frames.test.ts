import { describe, expect, it } from "vitest";
import { renderInverseThinkingHtml } from "../src/inverse-thinking-renderer.js";
import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";

describe("inverse-thinking creative frames", () => {
  it("changes frame class without changing semantic case content", () => {
    const detective = renderInverseThinkingHtml({ ...inverseThinkingFixture, frame: "detective_case" });
    const neutral = renderInverseThinkingHtml({ ...inverseThinkingFixture, frame: "neutral" });

    expect(detective).toContain("frame-detective");
    expect(neutral).toContain("frame-neutral");
    expect(detective).toContain("I have visited Da Nang yesterday");
    expect(neutral).toContain("I have visited Da Nang yesterday");
  });
});
