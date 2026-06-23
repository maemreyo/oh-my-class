import { describe, expect, it } from "vitest";
import { renderArtifact, renderTemplate } from "../src/renderer.js";
import { sanitizeHtml } from "../src/sanitizer.js";
import { inlineCss, validateNoExternalUrls } from "../src/inline-assets.js";
import type { ArtifactContent } from "@oh-my-class/schemas";

const mockArtifact: ArtifactContent = {
	artifact_type: "lesson",
	theme: "default",
	title: "Test Lesson",
	sections: [{ title: "Intro", content: "Some content" }],
	metadata: {},
	accessibility: { language: "en", alt_texts: {} },
};

// ── renderArtifact ────────────────────────────────────────────────────────────

describe("renderArtifact", () => {
	it("produces valid HTML with DOCTYPE", () => {
		const html = renderArtifact(mockArtifact);
		expect(html).toContain("<!DOCTYPE html>");
	});

	it("includes oh-my-class brand string", () => {
		const html = renderArtifact(mockArtifact);
		expect(html).toContain("oh-my-class");
	});

	it("inlines theme CSS (no external link tags)", () => {
		const html = renderArtifact(mockArtifact);
		expect(html).toContain("<style>");
		expect(html).not.toMatch(/<link\s/);
	});

	it("renders the artifact title", () => {
		const html = renderArtifact(mockArtifact);
		expect(html).toContain("Test Lesson");
	});

	it("renders section content", () => {
		const html = renderArtifact(mockArtifact);
		expect(html).toContain("Some content");
	});

	it("uses lang attribute from accessibility", () => {
		const html = renderArtifact(mockArtifact);
		expect(html).toContain('lang="en"');
	});

	it("uses vi lang when accessibility.language is vi", () => {
		const artifact: ArtifactContent = {
			...mockArtifact,
			accessibility: { language: "vi", alt_texts: {} },
		};
		const html = renderArtifact(artifact);
		expect(html).toContain('lang="vi"');
	});

	it("throws for unknown artifact type", () => {
		const badArtifact = { ...mockArtifact, artifact_type: "unknown" } as ArtifactContent;
		expect(() => renderArtifact(badArtifact)).toThrow("Unknown artifact type");
	});

	it("renders all supported artifact types without throwing", () => {
		const types: ArtifactContent["artifact_type"][] = [
			"lesson", "worksheet", "quiz", "drill", "recap", "infographic",
		];
		for (const artifact_type of types) {
			const html = renderArtifact({ ...mockArtifact, artifact_type });
			expect(html).toContain("<!DOCTYPE html>");
		}
	});

	it("has no external CDN links", () => {
		const html = renderArtifact(mockArtifact);
		expect(html).not.toMatch(/https?:\/\//);
	});

	it("strips injected script tags", () => {
		const maliciousArtifact: ArtifactContent = {
			...mockArtifact,
			sections: [{ title: "Safe", content: "<script>alert(1)</script>" }],
		};
		const html = renderArtifact(maliciousArtifact);
		expect(html).not.toContain("<script>");
	});
});

// ── renderTemplate ────────────────────────────────────────────────────────────

describe("renderTemplate", () => {
	it("returns a string", () => {
		const result = renderTemplate("Hello <%= it.name %>", { name: "World" });
		expect(typeof result).toBe("string");
	});

	it("renders Eta template expressions", () => {
		const result = renderTemplate("Hello <%= it.name %>", { name: "World" });
		expect(result).toContain("World");
	});

	it("returns empty string for empty template", () => {
		const result = renderTemplate("", {});
		expect(result).toBe("");
	});

	it("renders static content unchanged", () => {
		const result = renderTemplate("Static text", {});
		expect(result).toBe("Static text");
	});
});

// ── sanitizeHtml ──────────────────────────────────────────────────────────────

describe("sanitizeHtml", () => {
	it("removes script blocks", () => {
		const html = '<div>Safe</div><script>alert("xss")</script>';
		const clean = sanitizeHtml(html);
		expect(clean).not.toContain("<script>");
		expect(clean).toContain("Safe");
	});

	it("removes inline script with attributes", () => {
		const html = '<script type="text/javascript">evil()</script><p>ok</p>';
		const clean = sanitizeHtml(html);
		expect(clean).not.toContain("<script");
		expect(clean).toContain("ok");
	});

	it("removes onclick event handlers", () => {
		const html = '<div onclick="alert(1)">Safe</div>';
		const clean = sanitizeHtml(html);
		expect(clean).not.toContain("onclick");
		expect(clean).toContain("Safe");
	});

	it("removes onerror event handlers", () => {
		const html = '<img src="x" onerror="alert(1)">';
		const clean = sanitizeHtml(html);
		expect(clean).not.toContain("onerror");
	});

	it("removes onload event handlers", () => {
		const html = "<body onload=\"steal()\">content</body>";
		const clean = sanitizeHtml(html);
		expect(clean).not.toContain("onload");
		expect(clean).toContain("content");
	});

	it("removes iframe tags", () => {
		const html = "<div>ok</div><iframe src=\"evil.com\"></iframe>";
		const clean = sanitizeHtml(html);
		expect(clean).not.toContain("iframe");
		expect(clean).toContain("ok");
	});

	it("removes embed tags", () => {
		const html = "<div>ok</div><embed src=\"evil.swf\">";
		const clean = sanitizeHtml(html);
		expect(clean).not.toContain("embed");
	});

	it("preserves safe content", () => {
		const html = '<div class="content"><p>Hello</p></div>';
		const clean = sanitizeHtml(html);
		expect(clean).toContain("Hello");
		expect(clean).toContain('class="content"');
	});

	it("preserves style tags", () => {
		const html = "<style>body { color: red; }</style><p>text</p>";
		const clean = sanitizeHtml(html);
		expect(clean).toContain("<style>");
		expect(clean).toContain("color: red");
	});
});

// ── inlineCss / validateNoExternalUrls ───────────────────────────────────────

describe("inlineCss", () => {
	it("injects style tag before </head>", () => {
		const html = "<html><head></head><body>hi</body></html>";
		const result = inlineCss(html, "body { color: red; }");
		expect(result).toContain("<style>");
		expect(result).toContain("color: red");
		expect(result.indexOf("<style>")).toBeLessThan(result.indexOf("</head>"));
	});

	it("prepends style tag when no </head>", () => {
		const html = "<p>Hello</p>";
		const result = inlineCss(html, "p { margin: 0; }");
		expect(result).toContain("<style>");
		expect(result).toContain("Hello");
	});
});

describe("validateNoExternalUrls", () => {
	it("returns empty array for clean HTML", () => {
		const html = '<div class="ok"><p>Hello</p></div>';
		expect(validateNoExternalUrls(html)).toHaveLength(0);
	});

	it("detects external https URL in src", () => {
		const html = '<img src="https://cdn.example.com/image.png">';
		const violations = validateNoExternalUrls(html);
		expect(violations.length).toBeGreaterThan(0);
	});

	it("detects external http URL in href", () => {
		const html = '<link href="http://fonts.googleapis.com/css">';
		const violations = validateNoExternalUrls(html);
		expect(violations.length).toBeGreaterThan(0);
	});
});
