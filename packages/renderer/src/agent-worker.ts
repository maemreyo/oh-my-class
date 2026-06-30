import process from "node:process";

import { renderAgentArtifact } from "./agent-renderer.js";

export const RENDERER_VERSION = "0.1.0";
export const TEMPLATE_VERSION = "0.1.0";

type ArtifactRecord = Readonly<Record<string, unknown>>;

type WorkerRequest = Readonly<{
  renderer_version: string;
  template_version: string;
  artifact: unknown;
}>;

type WorkerResponse = Readonly<
  | { ok: true; html: string }
  | { ok: false; error: string; stderr?: string }
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

async function renderWorkerRequest(raw: string): Promise<WorkerResponse> {
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
