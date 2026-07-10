/**
 * SDE-06: "re-export needed" badge visibility logic.
 *
 * DOM rendering isn't this repo's convention for slide-deck-editor
 * components (see version-history-panel.test.ts) -- this tests the pure
 * decision function `shouldShowStalenessBadge` the component renders off of.
 */

import { describe, expect, it } from "vitest";
import { shouldShowStalenessBadge, type ExportStatus } from "./use-export-status";

function makeStatus(overrides: Partial<ExportStatus>): ExportStatus {
	return {
		artifact_id: "artifact-1",
		current_snapshot_id: "snap-2",
		latest_export: {
			export_id: "export-1",
			artifact_id: "artifact-1",
			snapshot_id: "snap-1",
			format: "pptx",
			storage_path: "exports/run-1/snap-1.pptx",
			created_at: "2026-07-09T10:00:00Z",
		},
		stale: true,
		...overrides,
	};
}

describe("shouldShowStalenessBadge", () => {
	it("shows the badge when the latest export lags the current snapshot", () => {
		expect(shouldShowStalenessBadge(makeStatus({ stale: true }))).toBe(true);
	});

	it("hides the badge when the latest export matches the current snapshot", () => {
		expect(shouldShowStalenessBadge(makeStatus({ stale: false }))).toBe(false);
	});

	it("hides the badge while the query hasn't resolved yet (no false positive on loading)", () => {
		expect(shouldShowStalenessBadge(undefined)).toBe(false);
	});
});
