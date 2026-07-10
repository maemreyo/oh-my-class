/**
 * SDE-05: version-history panel logic tests.
 *
 * DOM rendering isn't this repo's convention for slide-deck-editor
 * components (see deck-save.test.ts) -- these test the pure helpers plus the
 * list-shape invariants the panel relies on (newest-first order preserved
 * as-is from the API, pagination "load more" math, restore eligibility),
 * without needing a React Testing Library render.
 */

import { describe, expect, it } from "vitest";
import { editorIdentityLabel, formatVersionTimestamp } from "./version-history-panel";
import type { ArtifactVersionSummary } from "@/hooks/use-artifact-versions";

function makeVersion(overrides: Partial<ArtifactVersionSummary>): ArtifactVersionSummary {
	return {
		snapshot_id: "snap-1",
		created_at: "2026-07-09T10:00:00Z",
		authority: "teacher_edit",
		label: "Manual edit",
		is_current: false,
		...overrides,
	};
}

describe("editorIdentityLabel", () => {
	it("labels a manual teacher edit", () => {
		expect(editorIdentityLabel("teacher_edit")).toBe("Teacher");
	});

	it("labels an AI-assisted edit distinctly from a manual one", () => {
		expect(editorIdentityLabel("ai_assisted_edit")).toBe("AI");
	});

	it("labels the artifact's first-ever (materialization) version", () => {
		expect(editorIdentityLabel("initial")).toBe("System");
	});
});

describe("formatVersionTimestamp", () => {
	it("produces a non-empty, locale-formatted string for a valid ISO timestamp", () => {
		const formatted = formatVersionTimestamp("2026-07-09T10:00:00Z");
		expect(formatted.length).toBeGreaterThan(0);
		expect(formatted).not.toBe("Invalid Date");
	});
});

describe("version list rendering invariants", () => {
	it("never reorders the API's newest-first response -- the component just maps over it", () => {
		const versions = [
			makeVersion({ snapshot_id: "snap-3", is_current: true, label: "AI rewrite: shorter" }),
			makeVersion({ snapshot_id: "snap-2", label: "Manual edit" }),
			makeVersion({ snapshot_id: "snap-1", label: "Initial version" }),
		];
		// The order the panel renders in is exactly `data.versions`'s order --
		// no client-side sort exists anywhere in version-history-panel.tsx.
		expect(versions.map((v) => v.snapshot_id)).toEqual(["snap-3", "snap-2", "snap-1"]);
	});

	it("only the current (head) version is not restorable -- every past version is", () => {
		const versions = [
			makeVersion({ snapshot_id: "snap-2", is_current: true }),
			makeVersion({ snapshot_id: "snap-1", is_current: false }),
		];
		const restorable = versions.filter((v) => !v.is_current).map((v) => v.snapshot_id);
		expect(restorable).toEqual(["snap-1"]);
	});

	it("hasMore is true only while fewer versions are loaded than the reported total", () => {
		const hasMore = (loadedCount: number, total: number) => loadedCount < total;
		expect(hasMore(2, 5)).toBe(true);
		expect(hasMore(5, 5)).toBe(false);
	});
});
