import { describe, expect, test } from "vitest";

import type { LessonPlan, MethodologyMetadata } from "./lesson_plan.js";

const validMethodology: MethodologyMetadata = {
	tags: ["inverse_thinking", "why_wrong_reasoning"],
	target_skill_area: "reasoning",
	student_profile_notes: null,
	payloads: { inverse_thinking: null },
};

const typedPlan: LessonPlan = {
	topic: "Fractions",
	grade_level: "Grade 5",
	subject: "math",
	duration_minutes: 45,
	learning_objectives: [
		{ description: "Compare fractions", bloom_level: "understand", assessment_method: null },
	],
	methodology: validMethodology,
};

describe("generated LessonPlan methodology types", () => {
	test("expose methodology as a typed field", () => {
		expect(typedPlan.methodology?.tags).toEqual(["inverse_thinking", "why_wrong_reasoning"]);
	});
});
