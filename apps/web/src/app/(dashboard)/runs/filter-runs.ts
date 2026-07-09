import type { Run } from "@/types";

export interface RunFilters {
	keyword: string;
	artifactType: string; // "all" = no filter
}

export const ALL_ARTIFACT_TYPES = "all";

/** Title shown in RunCard — keep filter matching in sync with that fallback. */
function displayTitle(run: Run): string {
	return run.topic || `Run ${run.run_id}`;
}

export function filterRuns(runs: Run[], filters: RunFilters): Run[] {
	const keyword = filters.keyword.trim().toLowerCase();
	return runs.filter((run) => {
		if (keyword && !displayTitle(run).toLowerCase().includes(keyword)) {
			return false;
		}
		if (
			filters.artifactType !== ALL_ARTIFACT_TYPES &&
			!run.artifact_types?.includes(filters.artifactType)
		) {
			return false;
		}
		return true;
	});
}

export function collectArtifactTypes(runs: Run[]): string[] {
	return Array.from(
		new Set(runs.flatMap((run) => run.artifact_types ?? [])),
	).sort();
}
