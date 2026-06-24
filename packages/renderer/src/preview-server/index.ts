import type { Application } from "express";
import { handlePreviewRequest } from "./router.js";
import { previewStore } from "./store.js";

export { previewStore };
export { buildIframeEmbed } from "./iframe-wrapper.js";
export { buildCSPHeader, buildSandboxAttribute } from "./csp.js";
export { PreviewStore } from "./store.js";

export function mountPreviewServer(app: Application): void {
  app.get("/api/preview/:runId", handlePreviewRequest);
}

let _cleanupInterval: ReturnType<typeof setInterval> | null = null;

export function startCleanup(intervalMs = 30 * 60 * 1000): void {
  _cleanupInterval = setInterval(() => {
    const purged = previewStore.purgeExpired();
    if (purged > 0)
      console.info(`[preview-server] Purged ${purged} expired artifacts`);
  }, intervalMs);
}

export function stopCleanup(): void {
  if (_cleanupInterval) clearInterval(_cleanupInterval);
  _cleanupInterval = null;
}
