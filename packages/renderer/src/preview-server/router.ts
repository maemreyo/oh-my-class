import type { Request, Response } from "express";
import { previewStore } from "./store.js";
import { buildCSPHeader } from "./csp.js";
import type { ArtifactType } from "../contracts/index.js";

export function handlePreviewRequest(req: Request, res: Response): void {
  const runId = Array.isArray(req.params.runId) ? req.params.runId[0] : req.params.runId;
  const artifact = previewStore.get(runId);

  if (!artifact) {
    res.status(404).json({ error: "Preview expired or not found", runId });
    return;
  }

  const csp = buildCSPHeader(artifact.type as ArtifactType);

  res
    .setHeader("Content-Type", "text/html; charset=utf-8")
    .setHeader("Content-Security-Policy", csp)
    .setHeader("X-Frame-Options", "SAMEORIGIN")
    .setHeader("X-Content-Type-Options", "nosniff")
    .setHeader("Cache-Control", "no-store")
    .status(200)
    .send(artifact.html);
}
