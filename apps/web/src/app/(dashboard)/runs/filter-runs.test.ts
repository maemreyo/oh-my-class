import { describe, expect, it } from "vitest";
import type { Run } from "@/types";
import { ALL_ARTIFACT_TYPES, collectArtifactTypes, filterRuns } from "./filter-runs";

const runs: Run[] = [
	{ run_id: "1", status: "completed", topic: "Photosynthesis", artifact_types: ["slide_deck"] },
	{ run_id: "2", status: "running", topic: "Fractions 101", artifact_types: ["worksheet"] },
	{ run_id: "3", status: "completed", artifact_types: ["slide_deck", "quiz"] },
];

describe("filterRuns", () => {
	it("narrows by keyword (case-insensitive, matches run_id fallback title)", () => {
		expect(filterRuns(runs, { keyword: "photo", artifactType: ALL_ARTIFACT_TYPES })).toEqual([
			runs[0],
		]);
		expect(filterRuns(runs, { keyword: "run 3", artifactType: ALL_ARTIFACT_TYPES })).toEqual([
			runs[2],
		]);
	});

	it("narrows by artifact type", () => {
		expect(filterRuns(runs, { keyword: "", artifactType: "worksheet" })).toEqual([runs[1]]);
	});

	it("combines keyword and artifact type", () => {
		expect(filterRuns(runs, { keyword: "fractions", artifactType: "slide_deck" })).toEqual([]);
	});

	it("returns zero results when nothing matches", () => {
		expect(filterRuns(runs, { keyword: "nonexistent", artifactType: ALL_ARTIFACT_TYPES })).toEqual(
			[],
		);
	});

	it("clearing filters (empty keyword, 'all' type) restores the full list", () => {
		expect(filterRuns(runs, { keyword: "", artifactType: ALL_ARTIFACT_TYPES })).toEqual(runs);
	});
});

describe("collectArtifactTypes", () => {
	it("returns sorted unique artifact types across runs", () => {
		expect(collectArtifactTypes(runs)).toEqual(["quiz", "slide_deck", "worksheet"]);
	});
});
