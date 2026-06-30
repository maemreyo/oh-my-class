import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import {
	CREATIVE_FRAME_OPTIONS,
	DEFAULT_INVERSE_THINKING_CASE,
	InverseThinkingEditor,
	createRegenerationPayload,
	updateInverseThinkingCase,
	validateInverseThinkingDraft,
	updateWrongReasonDraft,
	validateWrongReasons,
} from "@/components/inverse-thinking-editor";

describe("InverseThinkingEditor progressive disclosure", () => {
	it("renders teaching approach selector without inverse controls by default", () => {
		const html = renderToStaticMarkup(<InverseThinkingEditor />);

		expect(html).toContain("Teaching approach");
		expect(html).toContain("Auto");
		expect(html).toContain("Standard");
		expect(html).toContain("Inverse Thinking");
		expect(html).not.toContain("Creative direction");
	});

	it("reveals creative direction, intensity, and student output controls when inverse thinking is selected", () => {
		const html = renderToStaticMarkup(
			<InverseThinkingEditor initialState={{ approach: "inverse_thinking" }} />,
		);

		expect(html).toContain("Creative direction");
		expect(html).toContain("Intensity");
		expect(html).toContain("Student output");
		for (const frame of CREATIVE_FRAME_OPTIONS) {
			expect(html).toContain(frame.label);
		}
	});
});

describe("InverseThinkingEditor structured case editing", () => {
	it("updates editable fields and validates with generated schema", () => {
		const draft = updateInverseThinkingCase(
			DEFAULT_INVERSE_THINKING_CASE,
			"disaster",
			"A student writes: I have visited Da Nang yesterday.",
		);

		expect(draft.disaster).toContain("Da Nang");
		expect(validateInverseThinkingDraft(draft)).toEqual([]);
	});

	it("splits key clue edits by line", () => {
		const draft = updateInverseThinkingCase(
			DEFAULT_INVERSE_THINKING_CASE,
			"key_clues",
			"finished time\nwrong tense\n",
		);

		expect(draft.key_clues).toEqual(["finished time", "wrong tense"]);
	});

	it("reports generated-schema validation paths for invalid edits", () => {
		const draft = updateInverseThinkingCase(DEFAULT_INVERSE_THINKING_CASE, "safe_zone", "");

		expect(validateInverseThinkingDraft(draft)).toContain("cases.0.safe_zone");
	});

	it("updates wrong reasons per distractor and reports missing options", () => {
		const draft = updateWrongReasonDraft({ A: "Cause, not contrast." }, "C", "Adds an idea, not contrast.");

		expect(draft.C).toBe("Adds an idea, not contrast.");
		expect(validateWrongReasons({ A: "because", B: "although", C: "and" }, "B", draft)).toEqual([]);
		expect(validateWrongReasons({ A: "because", B: "although", C: "and" }, "B", { A: "Cause." })).toContain("wrong_reasons.C");
	});
});

describe("InverseThinkingEditor regeneration and inspector", () => {
	it("creates scoped field and case regeneration payloads", () => {
		expect(createRegenerationPayload(DEFAULT_INVERSE_THINKING_CASE, "field", "disaster")).toEqual({
			scope: "field",
			case_id: "case-1",
			field: "disaster",
		});
		expect(createRegenerationPayload(DEFAULT_INVERSE_THINKING_CASE, "case")).toEqual({
			scope: "case",
			case_id: "case-1",
			field: undefined,
		});
	});

	it("renders preview iframe and inspector details with warnings", () => {
		const html = renderToStaticMarkup(
			<InverseThinkingEditor
				initialState={{
					approach: "inverse_thinking",
					creativeFrame: "detective_case",
					inspectorOpen: true,
					qualityWarnings: ["generic disaster"],
				}}
				renderedHtml="<!DOCTYPE html><html><body>Student preview</body></html>"
				onRegenerate={vi.fn()}
			/>,
		);

		expect(html).toContain("Student preview");
		expect(html).toContain("Methodology inspector");
		expect(html).toContain("Frame rationale");
		expect(html).toContain("Disaster-first sequence");
		expect(html).toContain("Key clues");
		expect(html).toContain("Safe-zone boundary");
		expect(html).toContain("generic disaster");
	});
});
