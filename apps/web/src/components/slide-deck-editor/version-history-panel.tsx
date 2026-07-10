"use client";

/**
 * SDE-05: linear, newest-first, restorable version history for one slide
 * deck artifact. Deliberately NOT a diff/side-by-side comparison view --
 * that's out of scope for this slice (ADR-047 decision 7). Kept as its own
 * component/section (not folded into `deck-editor.tsx`'s SDE-07 save flow)
 * per the concurrent-work note in SDE-05's issue.
 *
 * "Open read-only" reuses the exact same rendered-HTML iframe preview
 * `TeachingPacksSlideDeckPreview` already uses (`snapshotPreviewUrl`) --
 * there's no separate "read-mode" React block tree in this codebase (SDE-03's
 * block components are edit-only), so the rendered snapshot HTML *is* the
 * read-only view, and it's exactly what guarantees no edit affordances leak
 * in (it's static HTML in a sandboxed iframe).
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { snapshotPreviewUrl } from "@/hooks/use-teaching-packs";
import { ARTIFACT_VERSIONS_PAGE_SIZE, useArtifactVersions, useRestoreArtifactVersion, type ArtifactVersionSummary } from "@/hooks/use-artifact-versions";

export function VersionHistoryPanel({ runId, artifactId }: { readonly runId: string; readonly artifactId: string }) {
	const [loadedPages, setLoadedPages] = useState(1);
	const [openSnapshotId, setOpenSnapshotId] = useState<string | null>(null);
	const { data, isLoading, error } = useArtifactVersions(runId, artifactId, 0, loadedPages * ARTIFACT_VERSIONS_PAGE_SIZE);
	const restore = useRestoreArtifactVersion(runId, artifactId);

	if (isLoading) return <p className="text-sm text-muted-foreground">Loading version history...</p>;
	if (error || !data) return <p className="text-sm text-destructive">Could not load version history.</p>;

	const currentHead = data.versions.find((version) => version.is_current) ?? data.versions[0];
	const hasMore = data.versions.length < data.total;

	return (
		<div className="space-y-3">
			<p className="text-xs text-muted-foreground">{data.total} version{data.total === 1 ? "" : "s"} total. Newest first.</p>
			{/* Bounded render: only ever the loaded page(s), never the full unbounded lineage at once. */}
			<ul className="max-h-96 space-y-2 overflow-y-auto pr-1" aria-label="Version history">
				{data.versions.map((version) => (
					<VersionRow
						key={version.snapshot_id}
						version={version}
						canRestore={!version.is_current}
						isRestoring={restore.isPending && restore.variables?.versionSnapshotId === version.snapshot_id}
						onView={() => setOpenSnapshotId(version.snapshot_id)}
						onRestore={() => {
							if (!currentHead) return;
							restore.mutate({ versionSnapshotId: version.snapshot_id, baseSnapshotId: currentHead.snapshot_id });
						}}
					/>
				))}
			</ul>
			{hasMore ? (
				<Button type="button" variant="outline" size="sm" onClick={() => setLoadedPages((n) => n + 1)}>
					Load more
				</Button>
			) : null}
			{restore.isError ? <p className="text-sm text-destructive">{(restore.error as Error).message}</p> : null}

			<Dialog open={openSnapshotId !== null} onOpenChange={(open) => !open && setOpenSnapshotId(null)}>
				<DialogContent className="max-w-4xl">
					{openSnapshotId ? (
						<iframe
							title={`Version ${openSnapshotId} preview (read-only)`}
							src={snapshotPreviewUrl(runId, openSnapshotId, "teacher")}
							className="h-[70vh] w-full rounded-md border border-border bg-card"
							sandbox="allow-same-origin"
						/>
					) : null}
				</DialogContent>
			</Dialog>
		</div>
	);
}

function VersionRow({
	version,
	canRestore,
	isRestoring,
	onView,
	onRestore,
}: {
	readonly version: ArtifactVersionSummary;
	readonly canRestore: boolean;
	readonly isRestoring: boolean;
	readonly onView: () => void;
	readonly onRestore: () => void;
}) {
	return (
		<li className="flex items-center justify-between gap-3 rounded-md border border-border bg-card p-2 text-sm">
			<div className="min-w-0">
				<p className="truncate font-medium">
					{version.label}
					{version.is_current ? <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">Current</span> : null}
				</p>
				<p className="text-xs text-muted-foreground">
					{formatVersionTimestamp(version.created_at)} &middot; {editorIdentityLabel(version.authority)}
				</p>
			</div>
			<div className="flex shrink-0 gap-2">
				<Button type="button" variant="ghost" size="sm" onClick={onView}>
					View
				</Button>
				{canRestore ? (
					<Button type="button" variant="outline" size="sm" disabled={isRestoring} onClick={onRestore}>
						{isRestoring ? "Restoring..." : "Restore"}
					</Button>
				) : null}
			</div>
		</li>
	);
}

// `authority` is the closest thing to "editor identity" this system tracks
// today -- there's no per-edit user id on `ArtifactSnapshot`/`RunEvent`
// (a run has exactly one owning teacher, no co-editor model per SDE-04), so
// "who" collapses to "the teacher" vs "AI", which is what the AC's own
// examples ("Manual edit," "AI rewrite: shorter") already imply.
export function editorIdentityLabel(authority: string): string {
	if (authority === "ai_assisted_edit") return "AI";
	if (authority === "initial") return "System";
	return "Teacher";
}

export function formatVersionTimestamp(isoTimestamp: string): string {
	return new Date(isoTimestamp).toLocaleString();
}
