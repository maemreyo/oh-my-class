import { describe, expect, it } from "vitest";

import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";
import { createPluginRegistry, render, renderBatch, RendererErrorCode, rendererPluginMetadata } from "../src/renderer.js";
import type { ArtifactKindPlugin, RenderContext } from "../src/renderer.js";
import { rootCauseSessionPlugin } from "../src/plugins/specialty-artifact-ui.js";
import type { RootCauseSessionData } from "../src/contracts/root-cause-session.js";
import type { VideoRouteData } from "../src/contracts/video-route.js";

const currentDir = dirname(fileURLToPath(import.meta.url));
const interactivityPath = join(currentDir, "../src/artifact-ui/interactivity.js");

const rootCauseData: RootCauseSessionData = {
  title: "Future Perfect vs Continuous",
  subtitle: "Root-cause reasoning session",
  subject: "English",
  gradeLevel: "Grade 10",
  lang: "vi",
  sessionCode: "RC-U1-L1",
  difficulty: "mid",
  estimatedMinutes: 45,
  targetConcept: "Future Perfect",
  anchorTimeline: [{
    id: "a1",
    label: "T+0",
    event: "Học sinh gặp câu đầu tiên",
    significance: "Điểm neo ban đầu",
    isKeyAnchor: true,
  }],
  comparisons: [{
    id: "c1",
    constant: "Same future deadline",
    variants: [{ label: "Completed", value: "will have finished", isControl: true }],
    insight: "Completion before a future anchor is the deciding signal.",
  }],
  scenarioAnchors: [{ id: "s1", scenario: "Deadline tomorrow", connection: "Future anchor" }],
  generalizationCheckpoints: [{
    id: "g1",
    learnerClaim: "Will have + V3 diễn tả hành động hoàn thành trước mốc tương lai",
    verdict: "confirmed",
    evidence: "Ví dụ thực tế",
  }],
  teacherNotes: "TEACHER_NOTE_ONLY",
};

const videoRouteData: VideoRouteData = {
  title: "Airport Listening Route",
  subject: "English",
  gradeLevel: "Grade 9",
  unit: "Unit 2",
  estimatedMinutes: 25,
  videoMetadata: { videoDuration: "3:20", videoTitle: "Airport check-in", channel: "Teacher channel" },
  stations: [
    { code: "GA01", title: "Khởi động", description: "Xem 15 giây đầu, đoán chủ đề.", catIndex: 1 },
    { code: "GA02", title: "Nghe lần 1", description: "Nghe toàn bài, ghi ý chính.", catIndex: 2, cues: [{ text: "listen for gate number" }] },
  ],
  completionBadge: "2/2 trạm hoàn thành",
  lang: "vi",
};

function context(audience: RenderContext["audience"]): RenderContext {
  return {
    audience,
    locale: "vi",
    theme: "default",
    renderMode: "export",
    requestId: `specialty-${audience}`,
    versions: { rendererVersion: "test-renderer" },
    assetPolicy: "inline-only",
  };
}

describe("specialty Artifact UI registry plugins", () => {
  it("declares metadata for inverse-thinking, root-cause session, and video route plugins", () => {
    const kinds = rendererPluginMetadata().map((plugin) => plugin.kind);

    expect(kinds).toContain("investigation-folder.inverse-thinking");
    expect(kinds).toContain("paper-dossier.root-cause-session");
    expect(kinds).toContain("transit-route.video-route");
  });

  it("renders all three specialty plugins through renderBatch with standalone manifests", async () => {
    const responses = await renderBatch({
      requests: [
        { kind: "investigation-folder.inverse-thinking", input: inverseThinkingFixture, context: context("student") },
        { kind: "paper-dossier.root-cause-session", input: rootCauseData, context: context("teacher") },
        { kind: "transit-route.video-route", input: videoRouteData, context: context("student") },
      ],
    });

    expect(responses.map((response) => response.manifest.kind)).toEqual([
      "investigation-folder.inverse-thinking",
      "paper-dossier.root-cause-session",
      "transit-route.video-route",
    ]);
    for (const response of responses) {
      expect(response.html).toMatch(/^<!DOCTYPE html>/);
      expect(response.html).not.toMatch(/https?:\/\//);
    }
    expect(responses[0]?.html).toContain('data-artifact-theme="investigation-folder"');
    expect(responses[1]?.html).toContain('data-managed-script-id="artifact-ui-interactivity"');
    expect(responses[2]?.html).toContain('data-artifact-theme="transit-route"');
  });

  it("keeps teacher-only inverse-thinking and root-cause fields out of student projections", async () => {
    const inverse = await render({ kind: "investigation-folder.inverse-thinking", input: inverseThinkingFixture, context: context("student") });
    const rootCause = await render({ kind: "paper-dossier.root-cause-session", input: rootCauseData, context: context("student") });

    expect(inverse.html).not.toContain('class="art-projection-flag"');
    expect(inverse.html).not.toContain('class="art-teacher-block"');
    expect(rootCause.html).not.toContain("TEACHER_NOTE_ONLY");
  });

  it("rejects malformed specialty inputs before rendering", async () => {
    await expect(render({ kind: "transit-route.video-route", input: { ...videoRouteData, stations: [] }, context: context("student") })).rejects.toMatchObject({ code: RendererErrorCode.ValidationFailed });
    await expect(render({ kind: "investigation-folder.inverse-thinking", input: { ...inverseThinkingFixture, cases: [] }, context: context("student") })).rejects.toMatchObject({ code: RendererErrorCode.ValidationFailed });
  });

  it("fails closed when a declared managed script hash does not match", async () => {
    const brokenPlugin: ArtifactKindPlugin<ReturnType<typeof rootCauseSessionPlugin.adapt>> = {
      ...rootCauseSessionPlugin,
      kind: "paper-dossier.root-cause-session-broken-script",
      managedScripts: [{ id: "artifact-ui-interactivity", sourcePath: interactivityPath, sha256: "0".repeat(64) }],
    };
    const registry = createPluginRegistry([brokenPlugin]);

    await expect(render({ kind: brokenPlugin.kind, input: rootCauseData, context: context("teacher") }, { registry })).rejects.toMatchObject({ code: RendererErrorCode.ExternalAsset });
  });
});
