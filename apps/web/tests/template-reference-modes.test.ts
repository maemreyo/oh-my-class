import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
	TEMPLATE_REFERENCE_MODES,
	renderTemplateReferencePreview,
	templateReferenceModeByTag,
} from "@/components/methodology/template-reference-modes";

const repoRoot = join(process.cwd(), "..", "..");
const brief = readFileSync(join(repoRoot, "docs", "reports", "template-reference-mode-briefs.md"), "utf8");

describe("template reference mode briefs", () => {
	it("inventories every raw reference template with primitives controls surfaces and quality expectations", () => {
		for (const mode of TEMPLATE_REFERENCE_MODES) {
			expect(brief).toContain(mode.sourceTemplate);
			expect(brief).toContain("Reusable primitives");
			expect(brief).toContain("Teacher controls");
			expect(brief).toContain("Renderer surfaces");
			expect(brief).toContain("Quality expectations");
			expect(brief).toContain("Offline adaptation");
		}
	});

	it("renders offline-safe standalone previews for each reference mode", () => {
		for (const mode of TEMPLATE_REFERENCE_MODES) {
			const html = renderTemplateReferencePreview(mode);

			expect(html).toContain("<!DOCTYPE html>");
			expect(html).toContain("oh-my-class");
			expect(html).toContain("viewport");
			expect(html).toContain("@media print");
			expect(html).not.toMatch(/https?:\/\//);
			expect(html).not.toMatch(/fonts\.googleapis|fonts\.gstatic|cdn|<script|<img/i);
		}
	});

	it("resolves reference modes by tag", () => {
		expect(templateReferenceModeByTag("key_reference")?.label).toBe("Key Reference");
		expect(templateReferenceModeByTag("missing_reference")).toBeNull();
	});
});
