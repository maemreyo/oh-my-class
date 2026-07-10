"use client";

/**
 * SDE-06: staleness check for the "re-export needed" badge -- compares the
 * artifact's latest export_records row (see
 * services/gateway/teaching_pack_export_store.py) to its current head
 * snapshot_id. Read-only: there is no mutation here, and deliberately no
 * "trigger re-export" call anywhere in this file -- re-export is always an
 * explicit teacher action taken elsewhere (out of scope for this hook), never
 * something fired automatically off an edit.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export type ExportRecordSummary = Readonly<{
	export_id: string;
	artifact_id: string;
	snapshot_id: string;
	format: string;
	storage_path: string;
	created_at: string;
}>;

export type ExportStatus = Readonly<{
	artifact_id: string;
	current_snapshot_id: string | null;
	latest_export: ExportRecordSummary | null;
	stale: boolean;
}>;

export function useExportStatus(runId: string, artifactId: string) {
	return useQuery({
		queryKey: ["export-status", runId, artifactId],
		queryFn: () => apiClient.get<ExportStatus>(`/teaching-packs/runs/${runId}/artifacts/${artifactId}/export-status`),
		enabled: !!runId && !!artifactId,
	});
}

/** The badge shows only when the fetch resolved AND came back stale --
 * loading/error/not-yet-fetched states never show it (no false positives
 * while data is unknown). */
export function shouldShowStalenessBadge(data: ExportStatus | undefined): boolean {
	return data?.stale === true;
}
