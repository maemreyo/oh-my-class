import { describe, expect, it } from "vitest";

import { ManifestStore } from "../src/core/manifest-store.js";
import type { RenderedDocument } from "../src/core/manifest-store.js";
import { ExportWriter } from "../src/exporters/export-writer.js";
import type { RenderContext, RenderManifest, RenderRequest } from "../src/renderer.js";

const manifest: RenderManifest = {
  kind: "quiz",
  rendererVersion: "test",
  pluginVersion: "0.1.0",
  templateVersion: "quiz-template-v1",
  themeVersion: "theme-resolver-v1",
  sanitizerPolicyVersion: "quiz-policy-v1",
  renderMode: "preview",
  locale: "vi",
  audience: "student",
  requestId: "test-001",
  renderedAt: new Date().toISOString(),
  contentHash: "abc123",
};

const quizInput = {
  title: "Q",
  subject: "S",
  gradeLevel: "G",
  timeLimit: 5,
  questions: [
    {
      id: "q1",
      prompt: "P?",
      options: [{ label: "A", text: "opt" }],
      answer: "A",
    },
  ],
};

const ctx: RenderContext = {
  audience: "student",
  locale: "vi",
  theme: "default",
  renderMode: "preview",
  requestId: "persist-quiz-001",
  versions: { rendererVersion: "test-v1" },
  assetPolicy: "inline-only",
};

describe("ManifestStore", () => {
  it("put and get round-trips a rendered document", () => {
    const store = new ManifestStore();
    const doc = store.put("req-001", "<html>test</html>", manifest);

    expect(doc.html).toBe("<html>test</html>");
    expect(doc.storedAt).toBeDefined();
    expect(doc.manifest.kind).toBe("quiz");

    const retrieved = store.get("req-001");
    expect(retrieved).toBeDefined();
    expect(retrieved!.html).toBe("<html>test</html>");
    expect(retrieved!.storedAt).toBe(doc.storedAt);
    expect(retrieved!.manifest.kind).toBe("quiz");
  });

  it("has returns true after put, false before", () => {
    const store = new ManifestStore();

    expect(store.has("req-002")).toBe(false);
    store.put("req-002", "<html>x</html>", manifest);
    expect(store.has("req-002")).toBe(true);
  });

  it("delete removes a stored document", () => {
    const store = new ManifestStore();
    store.put("req-003", "<html>y</html>", manifest);

    const deleted = store.delete("req-003");

    expect(deleted).toBe(true);
    expect(store.get("req-003")).toBeUndefined();
  });

  it("size tracks document count", () => {
    const store = new ManifestStore();

    expect(store.size()).toBe(0);

    store.put("req-a", "<html>a</html>", manifest);
    store.put("req-b", "<html>b</html>", manifest);
    expect(store.size()).toBe(2);

    store.delete("req-a");
    expect(store.size()).toBe(1);
  });

  it("get returns undefined for unknown requestId", () => {
    const store = new ManifestStore();

    expect(store.get("missing")).toBeUndefined();
  });
});

describe("ExportWriter", () => {
  it("write returns stored document by requestId", () => {
    const store = new ManifestStore();
    const expectedDoc = store.put("req-write-001", "<html>stored</html>", manifest);
    const writer = new ExportWriter(store);

    const result = writer.write("req-write-001");

    expect(result).toBeDefined();
    expect(result!.html).toBe("<html>stored</html>");
    expect(result!.storedAt).toBe(expectedDoc.storedAt);
    expect(result!.manifest.kind).toBe("quiz");
  });

  it("write returns undefined for missing requestId", () => {
    const store = new ManifestStore();
    const writer = new ExportWriter(store);

    expect(writer.write("missing")).toBeUndefined();
  });

  it("rerender renders fresh HTML and stores with manifest", async () => {
    const store = new ManifestStore();
    const writer = new ExportWriter(store);
    const request: RenderRequest = { kind: "quiz", input: quizInput, context: ctx };

    const doc = await writer.rerender(request);

    expect(doc.html).toMatch(/^<!DOCTYPE html>/i);
    expect(doc.manifest.kind).toBe("quiz");

    const stored = store.get("persist-quiz-001");
    expect(stored).toBeDefined();
    expect(stored!.html).toBe(doc.html);
    expect(stored!.manifest.contentHash).toBe(doc.manifest.contentHash);
  });

  it("storeResponse stores a pre-rendered document", () => {
    const store = new ManifestStore();
    const writer = new ExportWriter(store);

    const doc = writer.storeResponse({ html: "<div>test</div>", manifest }, "req-manual");

    expect(doc.html).toBe("<div>test</div>");
    expect(doc.manifest.kind).toBe("quiz");

    const retrieved = store.get("req-manual");
    expect(retrieved).toBeDefined();
    expect(retrieved!.html).toBe("<div>test</div>");
  });

  it("rerender creates new entry even if requestId already exists (re-render replaces)", async () => {
    const store = new ManifestStore();
    const writer = new ExportWriter(store);

    // Prime the store with an old entry under the same requestId
    store.put("persist-quiz-001", "<html>old</html>", {
      ...manifest,
      requestId: "persist-quiz-001",
      contentHash: "old-hash",
    });
    expect(store.size()).toBe(1);

    const request: RenderRequest = { kind: "quiz", input: quizInput, context: ctx };
    const doc = await writer.rerender(request);

    // Size must remain 1 — same key, not a second entry
    expect(store.size()).toBe(1);

    // The stored doc must reflect the fresh render, not the old placeholder
    const stored = store.get("persist-quiz-001");
    expect(stored).toBeDefined();
    expect(stored!.manifest.contentHash).not.toBe("old-hash");
    expect(stored!.manifest.contentHash).toBe(doc.manifest.contentHash);
  });
});
