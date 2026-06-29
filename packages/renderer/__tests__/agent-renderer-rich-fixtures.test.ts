import { describe, expect, it } from "vitest";

import { renderAgentArtifact } from "../src/agent-renderer.js";
import { ACTIVE_ARTIFACT_TYPES, richAgentArtifact } from "./rich-agent-fixtures.js";

const ANSWER_MARKERS = ["Answer key", "Correct answer", "Answer:", "Correct:", "Solution:"];

function assertStandaloneStudentHtml(html: string): void {
  expect(html).toContain("<!DOCTYPE html>");
  expect(html).toContain("oh-my-class");
  expect(html).not.toMatch(/https?:\/\//);
  for (const marker of ANSWER_MARKERS) {
    expect(html).not.toContain(marker);
  }
}

describe("renderAgentArtifact rich component fixtures", () => {
  it.each(ACTIVE_ARTIFACT_TYPES)("renders assessable standalone HTML for %s", async (artifactType) => {
    const html = await renderAgentArtifact(richAgentArtifact(artifactType));

    assertStandaloneStudentHtml(html);
    expect(html).toContain(`artifact--${artifactType}`);
    expect(html.length).toBeGreaterThan(4_000);
  });

  it("renders lesson components through the existing dispatcher/classes", async () => {
    const html = await renderAgentArtifact(richAgentArtifact("lesson"));

    expect(html).toContain("component-question-mc");
    expect(html).toContain("Teacher move");
    expect(html).toContain("Which fraction is equivalent to 1/2?");
  });

  it("renders every active artifact with more than a one-section shell", async () => {
    for (const artifactType of ACTIVE_ARTIFACT_TYPES) {
      const html = await renderAgentArtifact(richAgentArtifact(artifactType));
      const visibleBlocks = html.match(/<(section|article|li)\b/g) ?? [];

      expect(visibleBlocks.length, `${artifactType} should have multiple content blocks`).toBeGreaterThanOrEqual(4);
    }
  });
});
