import { SlideDeckBlockSchema } from "@oh-my-class/schemas";
import { describe, expect, it } from "vitest";
import { BLOCK_BODY_MAX } from "../block-constraints";
import { applyInteractionPromptEdit } from "./interaction-prompt-block";

const block = SlideDeckBlockSchema.parse({ block_id: "block-question", block_type: "interaction_prompt", body: "Original prompt" });

describe("applyInteractionPromptEdit", () => {
	it("accepts a valid prompt edit", () => {
		expect(applyInteractionPromptEdit(block, "New prompt text").body).toBe("New prompt text");
	});

	it("rejects an empty prompt and keeps the original body", () => {
		expect(applyInteractionPromptEdit(block, "").body).toBe("Original prompt");
	});

	it("clamps a prompt longer than the registry max", () => {
		const draft = "p".repeat(BLOCK_BODY_MAX + 5);
		expect(applyInteractionPromptEdit(block, draft).body).toHaveLength(BLOCK_BODY_MAX);
	});
});
