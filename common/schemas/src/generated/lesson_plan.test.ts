import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, test } from "vitest";

import { LessonPlanSchema } from "./lesson_plan.js";

const basePlan = {
	topic: "Fractions",
	grade_level: "Grade 5",
	subject: "math",
	duration_minutes: 45,
	learning_objectives: [
		{ description: "Compare fractions", bloom_level: "understand" },
	],
};

describe("generated LessonPlan methodology schema", () => {
	test("keeps methodology generated as a typed object schema", () => {
		const generated = readFileSync(new URL("./lesson_plan.ts", import.meta.url), "utf8");

		expect(generated).toContain('"methodology": z.union([MethodologyMetadataSchema, z.null()]).default(null)');
		expect(generated).toContain('"tags": z.array(z.enum(["concept_map"');
		expect(generated).not.toContain('"methodology": z.union([z.any(), z.null()])');
	});

	test("accepts valid typed methodology metadata", () => {
		const parsed = LessonPlanSchema.parse({
			...basePlan,
			methodology: { tags: ["inverse_thinking", "active_recall"] },
		});

		expect(parsed.methodology?.tags).toEqual(["inverse_thinking", "active_recall"]);
	});

	test("rejects arbitrary methodology JSON", () => {
		const result = LessonPlanSchema.safeParse({
			...basePlan,
			methodology: { tags: ["made_up"], arbitrary: true },
		});

		expect(result.success).toBe(false);
	});

	test("keeps null and omitted methodology valid during migration", () => {
		expect(LessonPlanSchema.parse({ ...basePlan, methodology: null }).methodology).toBeNull();
		expect(LessonPlanSchema.parse(basePlan).methodology).toBeNull();
	});

	test("rejects invalid methodology tags at compile time", () => {
		const directory = mkdtempSync(join(tmpdir(), "lesson-plan-methodology-"));
		const fixture = join(directory, "invalid-tag.ts");
		writeFileSync(
			fixture,
			`import type { MethodologyMetadata } from "${new URL("./lesson_plan.ts", import.meta.url).pathname}";

const invalidMethodology: MethodologyMetadata = {
	tags: ["not_a_methodology"],
	target_skill_area: null,
	student_profile_notes: null,
	payloads: { inverse_thinking: null },
};

void invalidMethodology;
`,
		);

		const result = spawnSync("pnpm", [
			"exec",
			"tsc",
			"--noEmit",
			"--strict",
			"--skipLibCheck",
			"--module",
			"NodeNext",
			"--moduleResolution",
			"NodeNext",
			"--target",
			"ES2022",
			fixture,
		], { encoding: "utf8" });
		rmSync(directory, { recursive: true, force: true });

		expect(result.status).not.toBe(0);
		expect(`${result.stdout}${result.stderr}`).toContain('"not_a_methodology"');
	});
});
