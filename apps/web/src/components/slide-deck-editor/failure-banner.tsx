"use client";

import { getSlideDeckFailureCopy } from "@/components/slide-deck-editor/failure-copy";

// The ADR-043 5-surface set (see packages/renderer/src/slide-deck-projection.ts).
export type SlideDeckRenderSurface = "student" | "presentation" | "teacher" | "print" | "review";

const NEXT_ACTION_LABEL: Readonly<Record<string, string>> = {
	regenerate: "Regenerate",
	revise_prompt: "Revise and regenerate",
	inspect_teacher_notes: "Review teacher notes",
	retry_export: "Retry export",
	contact_admin: "Contact support",
};

/** The two student-safe surfaces (ADR-043) — never show failure/debug UI. */
export function isStudentSafeSurface(surface: SlideDeckRenderSurface): boolean {
	return surface === "student" || surface === "presentation";
}

/**
 * Renders teacher-safe failure copy for a slide-deck failure code.
 *
 * SDH-11 AC: "Student-facing surfaces never show teacher recovery/debug
 * messages." `isStudentSafeSurface` gates this structurally, so there is no
 * code path where a student-facing render can show any failure/debug state
 * at all, regardless of what `code` it's called with.
 */
export function SlideDeckFailureBanner({ surface, code }: { readonly surface: SlideDeckRenderSurface; readonly code: string }) {
	if (isStudentSafeSurface(surface)) return null;

	const copy = getSlideDeckFailureCopy(code);
	const isScoped = copy.recoveryScope === "scoped";

	return (
		<div role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 p-3">
			<p className="text-xs font-semibold uppercase tracking-wide text-destructive">
				{isScoped ? "Repairing this slide" : "Full regeneration required"}
			</p>
			<p className="mt-1 text-sm text-foreground">{copy.message}</p>
			<p className="mt-2 text-sm font-medium text-muted-foreground">Next step: {NEXT_ACTION_LABEL[copy.nextAction]}</p>
		</div>
	);
}
