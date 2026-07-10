"use client";

import { useCallback, useEffect, useState } from "react";
import type { SlideDeckData, SlideDeckSlide } from "@oh-my-class/schemas";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { shouldShowStalenessBadge, useExportStatus } from "@/hooks/use-export-status";
import { SlideCanvas } from "./slide-canvas";
import { useDeckEditorDraft } from "./use-deck-editor-draft";
import { type EditBlockFn, saveDeckEdits } from "./deck-save";
import { handleNavigateAway } from "./deck-navigate-away";
import { VersionHistoryPanel } from "./version-history-panel";

/**
 * SDE-03 built this canvas as local-state-only. SDE-07 adds (below, kept
 * separate from the SDE-03 render tree so it's easy to tell apart from
 * SDE-05's concurrent version-history addition):
 *  - continuous localStorage draft mirroring + crash recovery (`useDeckEditorDraft`)
 *  - exactly one SDE-04 save call per explicit "Save" click or confirmed
 *    navigate-away, never per keystroke (`saveDeckEdits`)
 *  - 409 optimistic-lock conflict messaging that preserves the draft
 */
export function SlideDeckEditor({
	runId,
	artifactId,
	initialDeck,
	baseSnapshotId,
}: {
	readonly runId: string;
	/** SDE-05: the artifact id itself (stable regardless of which snapshot is
	 * currently head) -- used only for the version-history panel, which
	 * fetches its own snapshot ids and doesn't depend on `baseSnapshotId`
	 * having resolved. */
	readonly artifactId: string;
	readonly initialDeck: SlideDeckData;
	/** The artifact's current snapshot id at load time, for SDE-04's
	 * optimistic lock. `null` when the loading path hasn't resolved one yet
	 * (see the ponytail note below) -- Save stays disabled in that case
	 * rather than sending a request that's guaranteed to 404/409. */
	readonly baseSnapshotId: string | null;
}) {
	const { deck, updateDeck, hasUnsavedChanges, clearDraft } = useDeckEditorDraft(initialDeck.deck_id, initialDeck);
	const [slideIndex, setSlideIndex] = useState(0);
	const [snapshotId, setSnapshotId] = useState(baseSnapshotId);
	const [isSaving, setIsSaving] = useState(false);
	const [saveError, setSaveError] = useState<string | null>(null);
	// SDE-08: block ids whose current draft body came from an applied (but not
	// yet saved) AI rewrite -- `save()` tags exactly these blocks'
	// `content_version.created` event `authority: "ai_assisted_edit"`,
	// distinct from every other (manual) edit's default `"teacher_edit"`.
	const [aiAssistedBlockIds, setAiAssistedBlockIds] = useState<ReadonlySet<string>>(new Set());
	const currentSlide = deck.slides[slideIndex] ?? null;
	// SDE-06: read-only staleness check -- never triggers a re-export itself.
	// Re-export (when it exists) is always an explicit teacher action taken
	// elsewhere, never fired automatically off this query or off a save.
	const exportStatus = useExportStatus(runId, artifactId);

	function updateSlide(updated: SlideDeckSlide) {
		updateDeck((previous) => ({
			...previous,
			slides: previous.slides.map((slide) => (slide.slide_id === updated.slide_id ? updated : slide)),
		}));
	}

	const editBlock: EditBlockFn = useCallback(
		({ snapshotId: currentSnapshotId, blockId, newContent, authority }) =>
			apiClient.patch(`/teaching-packs/runs/${runId}/snapshots/${currentSnapshotId}/blocks/${blockId}`, {
				base_snapshot_id: currentSnapshotId,
				new_content: newContent,
				...(authority ? { authority } : {}),
			}),
		[runId],
	);

	const save = useCallback(async (): Promise<{ ok: boolean }> => {
		if (snapshotId === null) return { ok: false };
		setIsSaving(true);
		setSaveError(null);
		try {
			const result = await saveDeckEdits({
				originalDeck: initialDeck,
				currentDeck: deck,
				baseSnapshotId: snapshotId,
				editBlock,
				aiAssistedBlockIds,
			});
			setSnapshotId(result.snapshotId);
			if (result.ok) {
				clearDraft(); // only clear the local draft in the success branch -- never optimistically, never on failure.
				setAiAssistedBlockIds(new Set()); // those blocks' AI-authored bodies are now the server's head; a later edit is manual again.
			} else if (result.error) {
				setSaveError(result.error); // 409s and other failures alike keep the draft intact.
			}
			return { ok: result.ok };
		} finally {
			setIsSaving(false);
		}
	}, [deck, initialDeck, snapshotId, editBlock, clearDraft, aiAssistedBlockIds]);

	const handleBlockRewriteApplied = useCallback((blockId: string) => {
		setAiAssistedBlockIds((previous) => new Set(previous).add(blockId));
	}, []);

	// Tab close/refresh: rely on the browser's own native confirm prompt (no
	// custom async save can run in `beforeunload`); the already-persisted
	// localStorage draft is the actual safety net on return.
	useEffect(() => {
		function onBeforeUnload(event: BeforeUnloadEvent) {
			if (!hasUnsavedChanges) return;
			event.preventDefault();
			event.returnValue = "";
		}
		window.addEventListener("beforeunload", onBeforeUnload);
		return () => window.removeEventListener("beforeunload", onBeforeUnload);
	}, [hasUnsavedChanges]);

	function goBack() {
		void handleNavigateAway({
			hasUnsavedChanges,
			confirmLeave: () => window.confirm("You have unsaved edits. Save and leave, or cancel to keep editing?"),
			save,
			navigate: () => window.history.back(),
		});
	}

	return (
		<div className="flex h-full min-h-0 flex-1">
			<nav aria-label="Slide outline" className="w-56 shrink-0 space-y-2 overflow-y-auto border-r border-border bg-card p-3">
				<button type="button" onClick={goBack} className="mb-2 text-sm text-muted-foreground underline-offset-2 hover:underline">
					&larr; Back
				</button>
				{deck.slides.map((slide, index) => (
					<button
						key={slide.slide_id}
						type="button"
						onClick={() => setSlideIndex(index)}
						className={
							index === slideIndex
								? "w-full rounded-md border border-primary bg-muted p-2 text-left text-sm"
								: "w-full rounded-md border border-border bg-background p-2 text-left text-sm hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
						}
					>
						<span className="block text-xs text-muted-foreground">Slide {index + 1}</span>
						<span className="block font-medium">{slide.title}</span>
					</button>
				))}
			</nav>
			<div className="min-w-0 flex-1 overflow-y-auto p-6">
				<div className="mx-auto max-w-3xl space-y-4">
					<div className="flex items-center justify-between gap-4">
						<div className="flex min-w-0 items-center gap-2">
							<h1 className="min-w-0 truncate text-xl font-semibold">{deck.title}</h1>
							{shouldShowStalenessBadge(exportStatus.data) ? (
								<span
									role="status"
									title="This deck has been edited since its last export -- re-export to include the latest changes."
									className="shrink-0 rounded-full border border-amber-400/50 bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900 dark:border-amber-300/30 dark:bg-amber-900/30 dark:text-amber-200"
								>
									Re-export needed
								</span>
							) : null}
						</div>
						<div className="flex shrink-0 gap-2">
							<Dialog>
								<DialogTrigger asChild>
									<Button type="button" variant="ghost" size="sm">
										Version history
									</Button>
								</DialogTrigger>
								<DialogContent className="max-w-2xl">
									<VersionHistoryPanel runId={runId} artifactId={artifactId} />
								</DialogContent>
							</Dialog>
							<Button
								type="button"
								variant="outline"
								size="sm"
								disabled={!hasUnsavedChanges || isSaving || snapshotId === null}
								title={snapshotId === null ? "This deck wasn't loaded with a snapshot reference yet -- reload from the run's approval view." : undefined}
								onClick={() => void save()}
							>
								{isSaving ? "Saving..." : "Save changes"}
							</Button>
						</div>
					</div>
					{saveError ? (
						<div role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-foreground">
							{saveError}
						</div>
					) : null}
					{currentSlide ? (
						<SlideCanvas
							slide={currentSlide}
							onSlideChange={updateSlide}
							runId={runId}
							snapshotId={snapshotId}
							onBlockRewriteApplied={handleBlockRewriteApplied}
						/>
					) : (
						<p className="text-sm text-muted-foreground">No slides in this deck.</p>
					)}
				</div>
			</div>
		</div>
	);
}
