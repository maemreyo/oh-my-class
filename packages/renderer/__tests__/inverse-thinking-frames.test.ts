import { describe, expect, it } from "vitest";
import { renderInverseThinkingHtml } from "../src/inverse-thinking-renderer.js";
import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";

describe("inverse-thinking creative frames", () => {
  it("detective frame uses art-cover--folder--detective modifier", async () => {
    const detective = await renderInverseThinkingHtml({ ...inverseThinkingFixture, frame: "detective_case" });
    const neutral = await renderInverseThinkingHtml({ ...inverseThinkingFixture, frame: "neutral" });

    expect(detective).toContain("art-cover--folder--detective");
    expect(neutral).toContain("art-cover--folder--neutral");
    expect(detective).not.toContain("art-cover--folder--neutral");
    expect(neutral).not.toContain("art-cover--folder--detective");
  });

  it("both frames contain case content", async () => {
    const detective = await renderInverseThinkingHtml({ ...inverseThinkingFixture, frame: "detective_case" });
    const neutral = await renderInverseThinkingHtml({ ...inverseThinkingFixture, frame: "neutral" });

    // Both should contain case data from the fixture
    expect(detective).toContain("investigation-folder");
    expect(neutral).toContain("investigation-folder");
  });
});
