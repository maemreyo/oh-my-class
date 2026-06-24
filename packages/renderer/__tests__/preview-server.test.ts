import { describe, expect, it } from "vitest";
import { PreviewStore } from "../src/preview-server/store.js";
import { buildCSPHeader, buildSandboxAttribute } from "../src/preview-server/csp.js";
import { buildIframeEmbed } from "../src/preview-server/iframe-wrapper.js";
import type { ArtifactType } from "../src/contracts/index.js";

// ── PreviewStore ─────────────────────────────────────────────────────────────

describe("PreviewStore", () => {
  it("returns artifact before TTL", () => {
    const store = new PreviewStore(60_000);
    store.set("r1", "<html>test</html>", "quiz");
    expect(store.get("r1")?.html).toBe("<html>test</html>");
  });

  it("returns artifact type", () => {
    const store = new PreviewStore(60_000);
    store.set("r1", "<html>test</html>", "lesson");
    expect(store.get("r1")?.type).toBe("lesson");
  });

  it("returns null after TTL expired", async () => {
    const store = new PreviewStore(1); // 1ms TTL
    store.set("r2", "<html>x</html>", "quiz");
    await new Promise((r) => setTimeout(r, 10));
    expect(store.get("r2")).toBeNull();
  });

  it("returns null for missing runId", () => {
    const store = new PreviewStore(60_000);
    expect(store.get("nonexistent")).toBeNull();
  });

  it("delete removes the entry", () => {
    const store = new PreviewStore(60_000);
    store.set("r3", "<html>x</html>", "quiz");
    store.delete("r3");
    expect(store.get("r3")).toBeNull();
  });

  it("purgeExpired removes expired entries", async () => {
    const store = new PreviewStore(1); // 1ms TTL
    store.set("r4", "<html>x</html>", "quiz");
    store.set("r5", "<html>y</html>", "lesson");
    await new Promise((r) => setTimeout(r, 10));
    const count = store.purgeExpired();
    expect(count).toBe(2);
    expect(store.get("r4")).toBeNull();
    expect(store.get("r5")).toBeNull();
  });

  it("purgeExpired returns 0 when nothing expired", () => {
    const store = new PreviewStore(60_000);
    store.set("r6", "<html>x</html>", "quiz");
    const count = store.purgeExpired();
    expect(count).toBe(0);
  });
});

// ── buildCSPHeader ────────────────────────────────────────────────────────────

describe("buildCSPHeader", () => {
  it("interactive type includes script-src unsafe-inline", () => {
    const csp = buildCSPHeader("quiz");
    expect(csp).toContain("script-src 'unsafe-inline'");
  });

  it("static type blocks scripts", () => {
    const csp = buildCSPHeader("lesson");
    expect(csp).toContain("script-src 'none'");
  });

  it("answer_key (static) blocks scripts", () => {
    const csp = buildCSPHeader("answer_key");
    expect(csp).toContain("script-src 'none'");
  });

  it("flashcard_deck (interactive) allows scripts", () => {
    const csp = buildCSPHeader("flashcard_deck");
    expect(csp).toContain("script-src 'unsafe-inline'");
  });

  it("all types block external resources", () => {
    const types: ArtifactType[] = ["quiz", "lesson", "infographic", "drill", "worksheet"];
    for (const type of types) {
      const csp = buildCSPHeader(type);
      expect(csp).toContain("default-src 'none'");
      expect(csp).toContain("connect-src 'none'");
      expect(csp).toContain("img-src data:");
      expect(csp).toContain("font-src 'none'");
    }
  });

  it("blocks form submissions for all types", () => {
    const csp = buildCSPHeader("worksheet");
    expect(csp).toContain("form-action 'none'");
  });
});

// ── buildSandboxAttribute ─────────────────────────────────────────────────────

describe("buildSandboxAttribute", () => {
  it("never combines allow-scripts + allow-same-origin", () => {
    const types: ArtifactType[] = [
      "quiz", "lesson", "drill", "flashcard_deck",
      "worksheet", "recap", "answer_key",
    ];
    for (const type of types) {
      const sandbox = buildSandboxAttribute(type);
      const hasScripts = sandbox.includes("allow-scripts");
      const hasSameOrigin = sandbox.includes("allow-same-origin");
      expect(hasScripts && hasSameOrigin).toBe(false);
    }
  });

  it("interactive types get allow-scripts", () => {
    expect(buildSandboxAttribute("quiz")).toContain("allow-scripts");
    expect(buildSandboxAttribute("drill")).toContain("allow-scripts");
    expect(buildSandboxAttribute("flashcard_deck")).toContain("allow-scripts");
  });

  it("interactive types get allow-forms", () => {
    expect(buildSandboxAttribute("quiz")).toContain("allow-forms");
    expect(buildSandboxAttribute("worksheet")).toContain("allow-forms");
  });
});

// ── buildIframeEmbed ──────────────────────────────────────────────────────────

describe("buildIframeEmbed", () => {
  it("includes correct src path", () => {
    const embed = buildIframeEmbed("run-123", "quiz");
    expect(embed).toContain('src="/api/preview/run-123"');
  });

  it("includes sandbox attribute", () => {
    const embed = buildIframeEmbed("run-123", "quiz");
    expect(embed).toContain("sandbox=");
  });

  it("static type sandbox does not include allow-same-origin", () => {
    const embed = buildIframeEmbed("run-456", "lesson");
    expect(embed).not.toContain("allow-same-origin");
  });

  it("includes aria-label for accessibility", () => {
    const embed = buildIframeEmbed("run-123", "quiz");
    expect(embed).toContain("aria-label=");
  });
});
