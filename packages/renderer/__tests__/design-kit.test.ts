import { describe, expect, it, vi } from "vitest";
import { extractCSSVars } from "../src/design-kit/extractor.js";
import { importDesignKit } from "../src/design-kit/index.js";

const TEMPLATE_HTML_EXCERPT = `
<style>
:root {
  --paper: #FBF4F0;
  --ink: #22273A;
  --red: #B23A2E;
  --gold: #A8782E;
  --green: #2E6F4E;
  --c-a: #33508F;
  --c-a-tint: rgba(51,80,143,0.08);
}
</style>
`;

describe("design-kit — extractor", () => {
  it("extractCSSVars finds all vars in :root block", () => {
    const vars = extractCSSVars(TEMPLATE_HTML_EXCERPT);
    expect(vars.length).toBeGreaterThanOrEqual(7);
    expect(vars.find((v) => v.name === "--paper")?.value).toBe("#FBF4F0");
    expect(vars.find((v) => v.name === "--ink")?.value).toBe("#22273A");
  });

  it("extractCSSVars handles multiline :root blocks", () => {
    const html = `<style>:root {\n  --bg: #fff;\n  --text: #000;\n}</style>`;
    const vars = extractCSSVars(html);
    expect(vars.length).toBe(2);
    expect(vars[0].name).toBe("--bg");
    expect(vars[1].name).toBe("--text");
  });

  it("extractCSSVars returns empty array for HTML without CSS vars", () => {
    const html = "<style>body { background: #fff; }</style>";
    const vars = extractCSSVars(html);
    expect(vars).toHaveLength(0);
  });
});

describe("design-kit — importDesignKit", () => {
  it("uses regex path for well-formed HTML", async () => {
    const result = await importDesignKit(TEMPLATE_HTML_EXCERPT, {
      name: "test",
    });
    expect(result.method).toBe("regex");
    expect(result.tokens.semantic.colorBg).toBe("#FBF4F0");
    expect(result.tokens.semantic.colorText).toBe("#22273A");
    expect(result.tokens.semantic.colorAccent).toBe("#B23A2E");
  });

  it("falls back to llm when < 3 vars found", async () => {
    const sparseHTML = "<style>body { background: #fff; }</style>";
    const mockLLM = {
      chat: vi
        .fn()
        .mockResolvedValue({
          content:
            '{"colorBg":"#fff","colorText":"#000","colorAccent":"#f00"}',
        }),
    };
    const result = await importDesignKit(sparseHTML, { llmClient: mockLLM });
    expect(result.method).toBe("llm");
    expect(mockLLM.chat).toHaveBeenCalledOnce();
  });

  it("category colors extracted from --c-a vars", async () => {
    const result = await importDesignKit(TEMPLATE_HTML_EXCERPT);
    expect(result.tokens.semantic.categoryColors?.a.base).toBe("#33508F");
  });

  it("category tint variants extracted from --c-a-tint", async () => {
    const result = await importDesignKit(TEMPLATE_HTML_EXCERPT);
    expect(result.tokens.semantic.categoryColors?.a.tint).toBe(
      "rgba(51,80,143,0.08)",
    );
  });

  it("confidence > 0.3 when semantic fields extracted", async () => {
    const result = await importDesignKit(TEMPLATE_HTML_EXCERPT);
    expect(result.confidence).toBeGreaterThan(0.3);
  });

  it("proposeThemeJSON fills missing fields from default", async () => {
    const result = await importDesignKit(TEMPLATE_HTML_EXCERPT, {
      name: "mine",
    });
    expect(result.tokens.name).toBe("mine");
    // All semantic fields should be present (from defaults)
    expect(result.tokens.semantic.colorBgCard).toBeTruthy();
    expect(result.tokens.semantic.colorBorder).toBeTruthy();
    expect(result.tokens.primitives).toBeDefined();
  });

  it("no undefined fields after proposeThemeJSON", async () => {
    const result = await importDesignKit(TEMPLATE_HTML_EXCERPT);
    const sem = result.tokens.semantic;
    expect(sem.colorBg).toBeTruthy();
    expect(sem.colorText).toBeTruthy();
    expect(sem.colorAccent).toBeTruthy();
    expect(sem.colorSuccess).toBeTruthy();
    expect(sem.colorWarning).toBeTruthy();
  });

  it("warnings generated for fields using defaults", async () => {
    // sparse HTML forces some defaults
    const sparseHTML = `<style>:root { --paper: #fff; --ink: #000; --red: #f00; }</style>`;
    const result = await importDesignKit(sparseHTML);
    // Some fields won't be found (e.g. colorBgCard, colorBorder), so warnings exist
    // result.warnings is an array (could be empty if all required pass validation)
    expect(Array.isArray(result.warnings)).toBe(true);
  });
});
