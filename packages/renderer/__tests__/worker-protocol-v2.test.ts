import { describe, expect, it } from "vitest";

import { RendererErrorCode } from "../src/renderer.js";
import { RENDERER_VERSION, renderWorkerRequest } from "../src/agent-worker.js";
import type { RenderContext } from "../src/renderer.js";

const context: RenderContext = {
  audience: "teacher",
  locale: "en",
  theme: "default",
  renderMode: "preview",
  requestId: "worker-v2-test",
  versions: { rendererVersion: RENDERER_VERSION },
  assetPolicy: "inline-only",
};

function workerPayload(input: unknown = { title: "Worker Fixture", body: "V2 render" }): string {
  return JSON.stringify({
    requestId: "worker-v2-test",
    kind: "fixture.echo",
    input,
    context,
  });
}

describe("worker protocol V2", () => {
  it("returns typed success envelopes with manifest diagnostics and metrics", async () => {
    const response = await renderWorkerRequest(workerPayload());

    expect(response.ok).toBe(true);
    expect("manifest" in response).toBe(true);
    if (response.ok && "manifest" in response) {
      expect(response.html).toContain("Worker Fixture");
      expect(response.manifest.kind).toBe("fixture.echo");
      expect(response.diagnostics).toEqual([]);
      expect(response.metrics.renderTimeMs).toBeGreaterThanOrEqual(0);
    }
  });

  it("returns typed malformed-json errors", async () => {
    const response = await renderWorkerRequest("{");

    expect(response.ok).toBe(false);
    if (!response.ok && typeof response.error !== "string") {
      expect(response.error.code).toBe("malformed_json");
      expect(response.error.retryable).toBe(false);
    }
  });

  it("returns typed version mismatch errors", async () => {
    const response = await renderWorkerRequest(JSON.stringify({
      requestId: "worker-v2-stale",
      kind: "fixture.echo",
      input: { title: "Worker Fixture", body: "V2 render" },
      context: { ...context, versions: { rendererVersion: "stale" } },
    }));

    expect(response.ok).toBe(false);
    if (!response.ok && typeof response.error !== "string") {
      expect(response.error.code).toBe(RendererErrorCode.ValidationFailed);
      expect(response.error.retryable).toBe(false);
    }
  });

  it("returns typed unknown-kind errors", async () => {
    const response = await renderWorkerRequest(JSON.stringify({
      requestId: "worker-v2-missing",
      kind: "missing.kind",
      input: {},
      context,
    }));

    expect(response.ok).toBe(false);
    if (!response.ok && typeof response.error !== "string") {
      expect(response.error.code).toBe(RendererErrorCode.UnknownKind);
      expect(response.error.retryable).toBe(false);
    }
  });

  it("returns typed validation errors", async () => {
    const response = await renderWorkerRequest(workerPayload({ title: "" }));

    expect(response.ok).toBe(false);
    if (!response.ok && typeof response.error !== "string") {
      expect(response.error.code).toBe(RendererErrorCode.ValidationFailed);
      expect(response.error.retryable).toBe(false);
    }
  });

  it("returns retryable typed internal errors", async () => {
    const response = await renderWorkerRequest(JSON.stringify({
      requestId: "worker-v2-internal",
      kind: "fixture.echo",
      input: { title: "Worker Fixture", body: "V2 render" },
      context: { ...context, versions: undefined },
    }));

    expect(response.ok).toBe(false);
    if (!response.ok && typeof response.error !== "string") {
      expect(response.error.code).toBe("internal_error");
      expect(response.error.retryable).toBe(true);
    }
  });
});
