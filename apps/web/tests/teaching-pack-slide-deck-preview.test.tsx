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
