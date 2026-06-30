import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import {
	ExportFormatChooser,
	STANDARD_ARTIFACTS,
	StandardGatePreview,
	StandardPackPreviewShell,
	exportFormatAvailability,
	type GatePreviewState,
} from "@/components/standard-pack/standard-pack-baseline";

const previewHtml = "<!DOCTYPE html><html><body>oh-my-class lesson preview</body></html>";

describe("StandardPackPreviewShell", () => {
	it("renders the ordinary artifact baseline with theme and print/mobile controls", () => {
		const html = renderToStaticMarkup(
			<StandardPackPreviewShell artifact="lesson" theme="ocean" html={previewHtml} viewport="mobile" />,
		);

		expect(html).toContain("Lesson");
		expect(html).toContain("Ocean theme");
		expect(html).toContain("Print");
		expect(html).toContain("Mobile");
		expect(html).toContain("sandbox=\"allow-same-origin\"");
		expect(html).not.toContain("allow-scripts");
	});

	it("lists all standard artifact types without special-mode semantics", () => {
		const html = renderToStaticMarkup(
			<StandardPackPreviewShell artifact="quiz" theme="forest" html={previewHtml} viewport="desktop" />,
		);

		for (const artifact of STANDARD_ARTIFACTS) {
			expect(html).toContain(artifact.label);
		}
		expect(html).not.toMatch(/inverse|disaster|clue|safe zone/i);
	});
});

describe("StandardGatePreview", () => {
	const states: readonly { readonly state: GatePreviewState; readonly primary: string; readonly secondary: string; readonly copy: string }[] = [
		{ state: "empty", primary: "Start blueprint", secondary: "Add lesson details", copy: "No standard pack content yet." },
		{ state: "loading", primary: "Generating", secondary: "View run log", copy: "Building the standard pack preview." },
		{ state: "quality_failed", primary: "Repair pack", secondary: "Open quality report", copy: "Quality gates found blocking issues." },
		{ state: "repair_in_progress", primary: "Repairing", secondary: "View repair plan", copy: "Repair is in progress." },
		{ state: "teacher_rejected", primary: "Revise content", secondary: "Review feedback", copy: "Teacher feedback requires changes." },
		{ state: "export_ready", primary: "Export pack", secondary: "Preview all artifacts", copy: "Ready for export." },
	];

	for (const item of states) {
		it(`shows actions and explanatory copy for ${item.state}`, () => {
			const html = renderToStaticMarkup(
				<StandardGatePreview gate="content_approval" state={item.state} completeness={83} qualityStatus="pass" exportReady />,
			);

			expect(html).toContain(item.primary);
			expect(html).toContain(item.secondary);
			expect(html).toContain(item.copy);
			expect(html).toContain("aria-live=\"polite\"");
		});
	}
});

describe("ExportFormatChooser", () => {
	it("disables unsupported format and artifact combinations with explanations", () => {
		const availability = exportFormatAvailability(["worksheet", "drill"]);

		expect(availability.html.enabled).toBe(false);
		expect(availability.html.explanation).toBe("HTML export needs a lesson artifact.");
		expect(availability.gift.enabled).toBe(false);
		expect(availability.gift.explanation).toBe("GIFT export needs a quiz artifact.");
	});

	it("renders accessible export readiness controls", () => {
		const html = renderToStaticMarkup(
			<ExportFormatChooser selectedArtifacts={["lesson", "quiz"]} selectedFormats={["html"]} />,
		);

		expect(html).toContain("Export readiness");
		expect(html).toContain("HTML");
		expect(html).toContain("GIFT");
		expect(html).toContain("aria-describedby");
		expect(html).not.toContain("disabled=\"\"");
	});
});
