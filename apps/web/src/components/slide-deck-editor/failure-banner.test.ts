import { describe, expect, it } from "vitest";
import { isStudentSafeSurface, type SlideDeckRenderSurface } from "./failure-banner";

describe("isStudentSafeSurface — SDH-11 student-facing suppression guard", () => {
	it("student and presentation are student-safe (no failure/debug UI)", () => {
		expect(isStudentSafeSurface("student")).toBe(true);
		expect(isStudentSafeSurface("presentation")).toBe(true);
	});

	it("teacher, print, and review are teacher-facing (may show recovery UI)", () => {
		const teacherFacing: readonly SlideDeckRenderSurface[] = ["teacher", "print", "review"];
		for (const surface of teacherFacing) {
			expect(isStudentSafeSurface(surface)).toBe(false);
		}
	});
});
