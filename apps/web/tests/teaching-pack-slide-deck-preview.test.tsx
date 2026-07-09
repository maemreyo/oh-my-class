import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { labelForArtifactType } from "@/components/teaching-packs-artifact-progress";
import {
	TeachingPacksSlideDeckPreview,
	createScopedFeedbackPayload,
	hasSlideDeckArtifact,
	onlineMediaWarnings,
	slideDeckFromEvent,
} from "@/components/teaching-packs-slide-deck-preview";
import { SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS, slideDeckPreviewUrl } from "@/hooks/use-teaching-packs";
import type { TeachingPackEventPayload } from "@/hooks/use-teaching-packs";

const deck = {
	deck_id: "deck-1",
	title: "Fractions deck",
	slides: [
		{
			slide_id: "slide-title",
			title: "Equivalent fractions",
			blocks: [
				{
					block_id: "block-title",
					body: "Equivalent fractions",
					media: {
						requires_network: true,
						fallback_text: "Sketch the model on the board.",
					},
				},
			],
			teacher_notes: {
				facilitation_notes: ["Ask students to compare the models."],
				answer_key_notes: ["Correct answer: b"],
			},
		},
		{
			slide_id: "slide-check",
			title: "Quick check",
			blocks: [{ block_id: "block-question", body: "Which model matches?" }],
			interactions: [{ interaction_id: "interaction-check", prompt: "Which model matches?" }],
		},
	],
} as const;

const event = {
	snapshot_ids: ["snapshot-1"],
	artifact_statuses: [{ artifact_id: "artifact-slide", artifact_type: "slide_deck", status: "passed", summary: "Ready", teacher_action: "Review" }],
	slide_deck_data: deck,
} satisfies TeachingPackEventPayload;

describe("TeachingPacksSlideDeckPreview", () => {
	it("renders slide-native controls for review", () => {
		const html = renderToStaticMarkup(<TeachingPacksSlideDeckPreview runId="run-1" event={event} />);

		expect(html).toContain("Slide-native review");
		expect(html).toContain("Student");
		expect(html).toContain("Teacher");
		expect(html).toContain("Print");
		expect(html).toContain("1 / 2");
		expect(html).toContain("Online media warning");
		expect(html).toContain("Scoped feedback");
	});

	it("detects slide deck payloads and labels them for teachers", () => {
		expect(hasSlideDeckArtifact(event)).toBe(true);
		expect(slideDeckFromEvent(event)?.deck_id).toBe("deck-1");
		expect(labelForArtifactType("slide_deck")).toBe("Slide deck");
	});

	it("keeps teacher-only guidance out of student helper output", () => {
		const warnings = onlineMediaWarnings(deck);

		expect(warnings).toEqual(["Equivalent fractions: Sketch the model on the board."]);
		expect(warnings.join(" ")).not.toContain("Correct answer");
	});

	it("keeps differentiation guidance out of the default student-safe render", () => {
		// ADR-045 (SDTF-05): default surface is "presentation" (student-safe),
		// so scaffold/stretch guidance must never appear in the static markup
		// even though the slide carries it.
		const deckWithGuidance = {
			...deck,
			slides: [
				{
					...deck.slides[0],
					differentiation_guidance: [
						{ level: "scaffold", guidance: "DIFF_LEAK_SCAFFOLD_TIP" },
						{ level: "stretch", guidance: "DIFF_LEAK_STRETCH_TIP" },
					],
				},
				deck.slides[1],
			],
		};
		const eventWithGuidance = { ...event, slide_deck_data: deckWithGuidance } satisfies TeachingPackEventPayload;

		const html = renderToStaticMarkup(<TeachingPacksSlideDeckPreview runId="run-1" event={eventWithGuidance} />);

		expect(html).not.toContain("DIFF_LEAK_SCAFFOLD_TIP");
		expect(html).not.toContain("DIFF_LEAK_STRETCH_TIP");
	});

	it("defaults the main canvas to the presentation surface via the typed display-preference seam", () => {
		// SDH-04: default view must be presentation (student-safe), never
		// teacher, and the iframe request must be built from the typed
		// SlideDeckDisplayPreferences shape -- no ad-hoc `?view=` string.
		const html = renderToStaticMarkup(<TeachingPacksSlideDeckPreview runId="run-1" event={event} />);

		const expectedUrl = slideDeckPreviewUrl("run-1", "snapshot-1", SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS);
		// react-dom/server HTML-escapes `&` in attribute values.
		expect(html).toContain(expectedUrl.replace(/&/g, "&amp;"));
		expect(html).not.toContain("?view=");
		expect(html).toContain("Presentation view");
		expect(html).toContain("Print &amp; sharing");
		// Teacher-only guidance stays outside the canvas and is not shown
		// by default, since the panel starts on the presentation surface.
		expect(html).not.toContain("Ask students to compare the models.");
		expect(html).not.toContain("Correct answer: b");
	});

	it("collapses the Print & sharing panel by default so the canvas stays uncluttered", () => {
		const html = renderToStaticMarkup(<TeachingPacksSlideDeckPreview runId="run-1" event={event} />);

		// A <details> without the `open` attribute renders collapsed.
		expect(html).toMatch(/<details[^>]*>\s*<summary/);
		expect(html).not.toMatch(/<details open/);
	});

	it("maps every display-preference field to the typed preview request, not string concatenation", () => {
		const url = slideDeckPreviewUrl("run-9", "snap-9", {
			surface: "print",
			print_layout: "continuous",
			slides_per_page: 4,
			chrome: "branded",
		});
		const parsed = new URL(url);

		expect(parsed.pathname).toBe("/teaching-packs/runs/run-9/snapshots/snap-9/preview");
		expect(parsed.searchParams.get("surface")).toBe("print");
		expect(parsed.searchParams.get("print_layout")).toBe("continuous");
		expect(parsed.searchParams.get("slides_per_page")).toBe("4");
		expect(parsed.searchParams.get("chrome")).toBe("branded");
	});

	it("creates stable scoped feedback targets", () => {
		const feedback = createScopedFeedbackPayload(deck, deck.slides[1], "interaction", " Keep answer teacher-only. ");

		expect(feedback).toEqual({
			scope: "interaction",
			deck_id: "deck-1",
			slide_id: "slide-check",
			block_id: undefined,
			interaction_id: "interaction-check",
			reason: "Keep answer teacher-only.",
		});
	});
});
