import { describe, expect, it } from "vitest";
import { renderInverseThinkingHtml } from "../src/inverse-thinking-renderer.js";
import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";

describe("inverse-thinking teacher-only separation", () => {
  it("student output has no art-teacher-block or art-projection-flag", async () => {
    const html = await renderInverseThinkingHtml(inverseThinkingFixture);

    expect(html).not.toContain('class="art-teacher-block"');
    expect(html).not.toContain('class="art-projection-flag"');
  });

  it("teacher_only output has art-projection-flag and teacher blocks", async () => {
    const html = await renderInverseThinkingHtml({ ...inverseThinkingFixture, artifactType: "teacher_only" });

    expect(html).toContain('class="art-projection-flag"');
    expect(html).toContain('class="art-teacher-block"');
  });

  it("teacher output contains teacher_only answer_key text", async () => {
    const html = await renderInverseThinkingHtml({ ...inverseThinkingFixture, artifactType: "teacher_only" });
    // The fixture's teacherOnly.answer_key content should be visible in teacher output
    expect(html).toContain(inverseThinkingFixture.teacherOnly.answer_key);
  });

  it("student output does NOT contain teacher_only answer_key text", async () => {
    const html = await renderInverseThinkingHtml(inverseThinkingFixture);
    expect(html).not.toContain(inverseThinkingFixture.teacherOnly.answer_key);
  });
});
