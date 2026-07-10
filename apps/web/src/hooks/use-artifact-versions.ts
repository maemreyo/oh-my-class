"use client";

/**
 * SDE-05: linear, newest-first, paginated version history for one artifact,
 * backed by the gateway endpoints added alongside
 * `services/gateway/routers/teaching_pack_previews.py`'s SDE-04 edit path:
 *   GET  /teaching-packs/runs/{runId}/artifacts/{artifactId}/versions
 *   POST /teaching-packs/runs/{runId}/artifacts/{artifactId}/versions/{snapshotId}/restore
 *
 * No diff/comparison view here (explicitly deferred, ADR-047 decision 7) --
 * just enough per version to list it, open it read-only (via the existing
 * `snapshotPreviewUrl` iframe preview), and restore it.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export const ARTIFACT_VERSIONS_PAGE_SIZE = 10;

export type ArtifactVersionSummary = Readonly<{
	snapshot_id: string;
	created_at: string;
	authority: string;
	label: string;
	is_current: boolean;
}>;

export type ArtifactVersionListResponse = Readonly<{
	run_id: string;
	artifact_id: string;
	total: number;
	limit: number;
	offset: number;
	versions: readonly ArtifactVersionSummary[];
}>;

export function useArtifactVersions(runId: string, artifactId: string, offset: number, limit: number = ARTIFACT_VERSIONS_PAGE_SIZE) {
	return useQuery({
		queryKey: ["artifact-versions", runId, artifactId, offset, limit],
		queryFn: () =>
			apiClient.get<ArtifactVersionListResponse>(
				`/teaching-packs/runs/${runId}/artifacts/${artifactId}/versions?limit=${limit}&offset=${offset}`,
			),
		enabled: !!runId && !!artifactId,
	});
}

type RestoreArtifactVersionResponse = Readonly<{
	run_id: string;
	artifact_id: string;
	restored_from_snapshot_id: string;
	base_snapshot_id: string;
	snapshot_id: string;
}>;

export function useRestoreArtifactVersion(runId: string, artifactId: string) {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: ({ versionSnapshotId, baseSnapshotId }: { versionSnapshotId: string; baseSnapshotId: string }) =>
			apiClient.post<RestoreArtifactVersionResponse>(
				`/teaching-packs/runs/${runId}/artifacts/${artifactId}/versions/${versionSnapshotId}/restore`,
				{ base_snapshot_id: baseSnapshotId },
			),
		onSuccess: () => {
			void queryClient.invalidateQueries({ queryKey: ["artifact-versions", runId, artifactId] });
		},
	});
}
