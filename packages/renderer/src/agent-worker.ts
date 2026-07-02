import process from "node:process";

import { renderAgentArtifact } from "./agent-renderer.js";
import { RendererError, RendererErrorCategory, RendererErrorCode, render } from "./renderer.js";
import type { RenderContext, RenderDiagnostic, RenderManifest, RenderMetrics } from "./renderer.js";

export const RENDERER_VERSION = "0.1.0";
export const TEMPLATE_VERSION = "0.1.0";

type ArtifactRecord = Readonly<Record<string, unknown>>;

type WorkerRequest = Readonly<{
  renderer_version: string;
  template_version: string;
  artifact: unknown;
}>;

type WorkerRenderRequest = Readonly<{
  requestId: string;
  kind: string;
  input: unknown;
  context: RenderContext;
}>;

type WorkerError = Readonly<{
  code: string;
  category: string;
  retryable: boolean;
  message: string;
  details?: Readonly<Record<string, unknown>>;
}>;

type WorkerResponse = Readonly<
  | { ok: true; html: string }
  | { ok: true; html: string; manifest: RenderManifest; diagnostics: readonly RenderDiagnostic[]; metrics: RenderMetrics }
  | { ok: false; error: string; stderr?: string }
  | { ok: false; error: WorkerError; diagnostics: readonly RenderDiagnostic[]; metrics?: RenderMetrics }
>;

function asRecord(value: unknown): ArtifactRecord {
  return value !== null && typeof value === "object" ? value as ArtifactRecord : {};
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function parseWorkerRequest(value: unknown): WorkerRequest {
  const record = asRecord(value);
  return {
    renderer_version: asString(record.renderer_version),
    template_version: asString(record.template_version),
    artifact: record.artifact,
  };
}

function assertCompatibleVersion(request: WorkerRequest): void {
  if (request.renderer_version !== RENDERER_VERSION) {
    throw new Error(`renderer_version mismatch: expected ${RENDERER_VERSION}, got ${request.renderer_version}`);
  }
  if (request.template_version !== TEMPLATE_VERSION) {
    throw new Error(`template_version mismatch: expected ${TEMPLATE_VERSION}, got ${request.template_version}`);
  }
}

function parseV2WorkerRequest(value: ArtifactRecord): WorkerRenderRequest {
  return {
    requestId: asString(value.requestId),
    kind: asString(value.kind),
    input: value.input,
    context: value.context as RenderContext,
  };
}

function assertCompatibleV2Version(request: WorkerRenderRequest): void {
  if (request.context.versions.rendererVersion !== RENDERER_VERSION) {
    throw new RendererError({
      code: RendererErrorCode.ValidationFailed,
      category: RendererErrorCategory.Validation,
      message: `rendererVersion mismatch: expected ${RENDERER_VERSION}, got ${request.context.versions.rendererVersion}`,
      details: { requestId: request.requestId },
    });
  }
}

function workerErrorFrom(error: Error): WorkerError {
  if (error instanceof RendererError) {
    return {
      code: error.code,
      category: error.category,
      retryable: error.retryable,
      message: error.message,
      details: error.details,
    };
  }
  return {
    code: "internal_error",
    category: "internal",
    retryable: true,
    message: error.message,
    details: { name: error.name, stack: error.stack },
  };
}

async function renderV2WorkerRequest(request: WorkerRenderRequest): Promise<WorkerResponse> {
  assertCompatibleV2Version(request);
  const response = await render({ kind: request.kind, input: request.input, context: request.context });
  return {
    ok: true,
    html: response.html,
    manifest: response.manifest,
    diagnostics: response.diagnostics,
    metrics: response.metrics,
  };
}

export async function renderWorkerRequest(raw: string): Promise<WorkerResponse> {
  try {
    const parsed = JSON.parse(raw);
    const record = asRecord(parsed);
    if ("kind" in record && "context" in record) {
      return await renderV2WorkerRequest(parseV2WorkerRequest(record));
    }
    const request = parseWorkerRequest(parsed);
    assertCompatibleVersion(request);
    return { ok: true, html: await renderAgentArtifact(request.artifact) };
  } catch (error) {
    if (error instanceof SyntaxError) {
      return {
        ok: false,
        diagnostics: [],
        error: {
          code: "malformed_json",
          category: "protocol",
          retryable: false,
          message: error.message,
        },
      };
    }
    if (error instanceof RendererError) {
      return { ok: false, diagnostics: [], error: workerErrorFrom(error) };
    }
    if (error instanceof Error) {
      return { ok: false, diagnostics: [], error: workerErrorFrom(error) };
    }
    throw error;
  }
}

export async function renderLegacyWorkerRequest(raw: string): Promise<WorkerResponse> {
  try {
    const request = parseWorkerRequest(JSON.parse(raw));
    assertCompatibleVersion(request);
    return { ok: true, html: await renderAgentArtifact(request.artifact) };
  } catch (error) {
    if (error instanceof Error) {
      return { ok: false, error: error.message, stderr: error.stack };
    }
    throw error;
  }
}

export async function runWorkerLoop(): Promise<void> {
  process.stdin.setEncoding("utf8");
  let buffer = "";
  for await (const chunk of process.stdin) {
    buffer += chunk;
    let newlineIndex = buffer.indexOf("\n");
    while (newlineIndex >= 0) {
      const raw = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (raw.length > 0) {
        process.stdout.write(`${JSON.stringify(await renderWorkerRequest(raw))}\n`);
      }
      newlineIndex = buffer.indexOf("\n");
    }
  }
}
