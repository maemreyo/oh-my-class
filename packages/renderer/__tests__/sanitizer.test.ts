import { describe, expect, it } from "vitest";
import { sanitize } from "../src/sanitizer/index.js";
import { buildDOMPurifyScript } from "../src/sanitizer/client-side-loader.js";

describe("sanitize — script blocking", () => {
  it("strips script tags from lesson", () => {
    const result = sanitize("<p>text</p><script>alert(1)</script>", "lesson");
    expect(result).not.toContain("<script>");
    expect(result).toContain("text");
  });

  it("strips script tags from quiz", () => {
    const result = sanitize('<p>q</p><script src="evil.js"></script>', "quiz");
    expect(result).not.toContain("<script");
  });
});

describe("sanitize — external URL blocking", () => {
  it("blocks external image src", () => {
    const result = sanitize('<img src="https://evil.com/img.png" alt="x">', "lesson");
    expect(result).not.toContain("https://evil.com");
  });

  it("allows data URI images", () => {
    const result = sanitize('<img src="data:image/png;base64,abc" alt="x">', "lesson");
    expect(result).toContain("data:image/png");
  });

  it("blocks external href", () => {
    const result = sanitize('<a href="https://evil.com">click</a>', "lesson");
    expect(result).not.toContain("https://evil.com");
  });
});

describe("sanitize — per-type configs", () => {
  it("quiz config allows radio inputs", () => {
    const result = sanitize('<input type="radio" name="q1" value="A">', "quiz");
    expect(result).toContain("<input");
    expect(result).toContain('type="radio"');
  });

  it("lesson config blocks input elements", () => {
    const result = sanitize('<input type="radio" name="q1" value="A">', "lesson");
    expect(result).not.toContain("<input");
  });

  it("worksheet config allows textarea", () => {
    const result = sanitize('<textarea name="ans" rows="3"></textarea>', "worksheet");
    expect(result).toContain("<textarea");
  });

  it("lesson config blocks textarea", () => {
    const result = sanitize('<textarea name="ans"></textarea>', "lesson");
    expect(result).not.toContain("<textarea");
  });

  it("infographic config allows SVG tags", () => {
    const svg = '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="#f00"/></svg>';
    const result = sanitize(svg, "infographic");
    expect(result).toContain("<svg");
    expect(result).toContain("<circle");
  });

  it("lesson config strips SVG", () => {
    const svg = '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>';
    const result = sanitize(svg, "lesson");
    expect(result).not.toContain("<svg");
  });

  it("answer_key config allows radio inputs (extends quiz)", () => {
    const result = sanitize('<input type="radio" name="q1" value="A">', "answer_key");
    expect(result).toContain("<input");
  });

  it("drill config allows radio inputs (extends quiz)", () => {
    const result = sanitize('<input type="radio" name="d1" value="B">', "drill");
    expect(result).toContain("<input");
  });
});

describe("sanitize — event handler stripping", () => {
  it("strips onclick from div (not in allowedAttributes)", () => {
    const result = sanitize('<div onclick="evil()">text</div>', "lesson");
    expect(result).not.toContain("onclick");
    expect(result).toContain("text");
  });
});

describe("sanitize — safe content preservation", () => {
  it("preserves class attributes", () => {
    const result = sanitize('<div class="component-mc">text</div>', "quiz");
    expect(result).toContain('class="component-mc"');
  });

  it("preserves aria-label attributes", () => {
    const result = sanitize('<button aria-label="Flip card">flip</button>', "flashcard_deck");
    expect(result).toContain('aria-label="Flip card"');
  });

  it("preserves style tags (theme CSS injection)", () => {
    const result = sanitize("<style>:root { --color-bg: #fff; }</style>", "lesson");
    expect(result).toContain("<style>");
    expect(result).toContain("--color-bg");
  });
});

describe("buildDOMPurifyScript", () => {
  it("returns a script tag", () => {
    const script = buildDOMPurifyScript();
    expect(script).toContain("<script>");
    expect(script).toContain("</script>");
  });

  it("includes DOMPurify placeholder", () => {
    const script = buildDOMPurifyScript();
    expect(script).toContain("__DOMPURIFY_INLINE__");
  });

  it("includes data-sanitize selector", () => {
    const script = buildDOMPurifyScript();
    expect(script).toContain("data-sanitize");
  });
});
