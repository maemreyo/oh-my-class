import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
	TeachingPackSectionEditor,
	createSectionEditPayload,
	initialSectionEdit,
} from "@/components/teaching-packs-scoped-rejection";

const artifacts = [
	{
		id: "lesson-1",
		type: "lesson",
		sections: [
			{
				section_id: "intro",
				title: "Intro",
				content: "Original intro.",
			},
		],
	},
] as const;

describe("TeachingPackSectionEditor", () => {
	it("renders structured fields for section edits", () => {
		const html = renderToStaticMarkup(
			<TeachingPackSectionEditor artifacts={artifacts} onSubmit={() => undefined} />,
		);

		expect(html).toContain("Structured section editor");
		expect(html).toContain("Replacement content");
		expect(html).toContain("Teacher rationale");
		expect(html).toContain("Original intro.");
	});

	it("creates a versioned scoped section edit payload", () => {
		const draft = initialSectionEdit(artifacts);

		expect(createSectionEditPayload({ ...draft, rationale: " Improve objective alignment. " })).toEqual({
			artifact_id: "lesson-1",
			section_id: "intro",
			component_id: undefined,
			replacement_content: "Original intro.",
			rationale: "Improve objective alignment.",
		});
	});
});
