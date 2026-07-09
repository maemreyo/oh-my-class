import { SlideDeckInteractionSchema } from "@oh-my-class/schemas";
import { describe, expect, it } from "vitest";
import { INTERACTION_PROMPT_MAX, OPTION_LABEL_MAX, RATIONALE_MAX } from "./block-constraints";
import {
	applyQuickCheckOptionLabelEdit,
	applyQuickCheckPromptEdit,
	applyQuickCheckRationaleEdit,
	setQuickCheckCorrectOption,
} from "./quick-check-interaction";

// Parsed through the real schema (fills in no_js_fallback/accessibility_label
// defaults) so the fixture stays valid as the contract evolves.
const interaction = SlideDeckInteractionSchema.parse({
	interaction_id: "interaction-check",
	interaction_type: "quick_check",
	prompt: "Original prompt?",
	answer_bearing: true,
	options: [
		{ option_id: "a", label: "Distractor A" },
		{ option_id: "b", label: "Correct answer" },
		{ option_id: "c", label: "Distractor B" },
	],
	teacher_only: {
		separation: "teacher_only_projection",
		correct_option_ids: ["b"],
		rationale: "Original rationale",
	},
});

describe("applyQuickCheckPromptEdit", () => {
	it("accepts a valid prompt edit", () => {
		expect(applyQuickCheckPromptEdit(interaction, "New prompt?").prompt).toBe("New prompt?");
	});

	it("rejects an empty prompt", () => {
		expect(applyQuickCheckPromptEdit(interaction, "").prompt).toBe("Original prompt?");
	});

	it("clamps a prompt longer than the registry max", () => {
		const draft = "q".repeat(INTERACTION_PROMPT_MAX + 20);
		expect(applyQuickCheckPromptEdit(interaction, draft).prompt).toHaveLength(INTERACTION_PROMPT_MAX);
	});
});

describe("applyQuickCheckOptionLabelEdit", () => {
	it("updates only the targeted option's label", () => {
		const result = applyQuickCheckOptionLabelEdit(interaction, "a", "Updated distractor");
		expect(result.options?.find((option) => option.option_id === "a")?.label).toBe("Updated distractor");
		expect(result.options?.find((option) => option.option_id === "b")?.label).toBe("Correct answer");
	});

	it("rejects an empty option label", () => {
		const result = applyQuickCheckOptionLabelEdit(interaction, "a", "");
		expect(result.options?.find((option) => option.option_id === "a")?.label).toBe("Distractor A");
	});

	it("clamps an option label longer than the registry max", () => {
		const draft = "o".repeat(OPTION_LABEL_MAX + 20);
		const result = applyQuickCheckOptionLabelEdit(interaction, "a", draft);
		expect(result.options?.find((option) => option.option_id === "a")?.label).toHaveLength(OPTION_LABEL_MAX);
	});
});

describe("setQuickCheckCorrectOption", () => {
	it("replaces correct_option_ids with a single new selection", () => {
		const result = setQuickCheckCorrectOption(interaction, "c");
		expect(result.teacher_only?.correct_option_ids).toEqual(["c"]);
	});
});

describe("applyQuickCheckRationaleEdit", () => {
	it("accepts a valid rationale edit", () => {
		expect(applyQuickCheckRationaleEdit(interaction, "New rationale").teacher_only?.rationale).toBe("New rationale");
	});

	it("rejects an empty rationale", () => {
		expect(applyQuickCheckRationaleEdit(interaction, "").teacher_only?.rationale).toBe("Original rationale");
	});

	it("clamps a rationale longer than the registry max", () => {
		const draft = "r".repeat(RATIONALE_MAX + 20);
		expect(applyQuickCheckRationaleEdit(interaction, draft).teacher_only?.rationale).toHaveLength(RATIONALE_MAX);
	});
});
