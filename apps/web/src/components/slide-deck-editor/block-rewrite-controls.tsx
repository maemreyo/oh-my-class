"use client";

import { useState } from "react";
import type { SlideDeckBlock } from "@oh-my-class/schemas";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { AiBlockRewriteConfirmModal } from "./ai-block-rewrite-confirm-modal";

/**
 * SDE-08: preset/freeform "Rewrite with AI" trigger, shared by every block
 * type via `SlideBlockEditor` (not duplicated per block component). Preset
 * keys mirror the backend's fixed `BLOCK_REWRITE_PRESETS` map
 * (`packages/agents/slide_deck_engine/phases/block_rewrite_llm.py`) -- add a
 * preset in both places together, they're a small fixed pair kept in sync by
 * hand rather than a shared codegen step.
 */
const REWRITE_PRESETS: Readonly<Record<string, string>> = {
	shorter: "Shorter",
	add_example: "Add an example",
	simplify: "Simplify language",
};

interface RewriteSuggestionResponse {
	readonly block_id: string;
	readonly before: string;
	readonly after: string;
}

/** Pure precedence rule extracted for unit testing without a DOM: freeform
 * text (once trimmed) wins when non-blank, otherwise the selected preset key
 * is sent -- mirrors the backend's `resolve_rewrite_instruction` precedence,
 * but the client only ever sends one of the two, never both. */
export function resolveRewriteSuggestionPayload(
	preset: string,
	freeform: string,
): { readonly preset: string } | { readonly instruction: string } {
	const trimmedFreeform = freeform.trim();
	return trimmedFreeform ? { instruction: trimmedFreeform } : { preset };
}

export function BlockRewriteControls({
	runId,
	snapshotId,
	block,
	blockLabel,
	onApply,
}: {
	readonly runId: string;
	/** `null` when the deck hasn't resolved a snapshot reference yet -- the
	 * trigger stays disabled rather than calling an endpoint guaranteed to fail. */
	readonly snapshotId: string | null;
	readonly block: SlideDeckBlock;
	/** Human label for the modal, e.g. "Paragraph text" or "Heading". */
	readonly blockLabel: string;
	/** Called ONLY on explicit "Apply" -- never on Cancel, never automatically. */
	readonly onApply: (newBody: string) => void;
}) {
	const [open, setOpen] = useState(false);
	const [preset, setPreset] = useState<string>("shorter");
	const [freeform, setFreeform] = useState("");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [candidate, setCandidate] = useState<RewriteSuggestionResponse | null>(null);

	async function requestSuggestion() {
		if (!snapshotId) return;
		setLoading(true);
		setError(null);
		try {
			const payload = resolveRewriteSuggestionPayload(preset, freeform);
			const result = await apiClient.post<RewriteSuggestionResponse>(
				`/teaching-packs/runs/${runId}/snapshots/${snapshotId}/blocks/${block.block_id}/rewrite-suggestion`,
				payload,
			);
			setCandidate(result);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Could not generate a rewrite suggestion.");
		} finally {
			setLoading(false);
		}
	}

	return (
		<div className="space-y-2">
			{!open ? (
				<Button type="button" variant="ghost" size="sm" disabled={!snapshotId} onClick={() => setOpen(true)}>
					Rewrite with AI
				</Button>
			) : (
				<div className="flex flex-wrap items-center gap-2 rounded-md border border-dashed border-border p-2">
					<select
						aria-label="Rewrite preset"
						className="rounded-md border border-border bg-background px-2 py-1 text-sm"
						value={preset}
						onChange={(event) => setPreset(event.target.value)}
					>
						{Object.entries(REWRITE_PRESETS).map(([key, label]) => (
							<option key={key} value={key}>
								{label}
							</option>
						))}
					</select>
					<input
						type="text"
						aria-label="Freeform rewrite instruction (optional)"
						placeholder="Or describe how to rewrite this (optional)"
						className="min-w-48 flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
						value={freeform}
						onChange={(event) => setFreeform(event.target.value)}
					/>
					<Button type="button" size="sm" disabled={loading} onClick={() => void requestSuggestion()}>
						{loading ? "Suggesting…" : "Suggest rewrite"}
					</Button>
					<Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>
						Close
					</Button>
				</div>
			)}
			{error ? <p className="text-xs text-destructive">{error}</p> : null}
			{candidate ? (
				<AiBlockRewriteConfirmModal
					blockLabel={blockLabel}
					before={candidate.before}
					after={candidate.after}
					onApply={() => {
						onApply(candidate.after);
						setCandidate(null);
						setOpen(false);
						setFreeform("");
					}}
					onCancel={() => setCandidate(null)}
				/>
			) : null}
		</div>
	);
}
