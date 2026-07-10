"use client";

import { Button } from "@/components/ui/button";

/**
 * SDX-04: minimal standalone before/after confirmation modal for AI-generated
 * alt text. SDE-08 (generic AI-rewrite confirmation modal, ADR-047 decision 4)
 * is not built yet — `.scratch/slide-deck-editor/issues/SDE-08-*.md` is still
 * `ready-for-agent` at the time of writing. This modal is deliberately scoped
 * to the same before/after + Accept/Reject shape SDE-08 will need, so a later
 * SDE-08 pass can consolidate this into its generic component instead of
 * building a second one from scratch.
 */
export function AiAltTextConfirmModal({
	before,
	after,
	onAccept,
	onReject,
}: {
	readonly before: string;
	readonly after: string;
	readonly onAccept: () => void;
	readonly onReject: () => void;
}) {
	return (
		<div
			role="dialog"
			aria-label="Confirm AI-generated alt text"
			className="space-y-3 rounded-md border border-border bg-popover p-3 shadow-md"
		>
			<p className="text-sm font-medium">AI-generated alt text</p>
			<div>
				<p className="text-xs font-medium text-muted-foreground">Current</p>
				<p className="text-sm">{before || "(empty)"}</p>
			</div>
			<div>
				<p className="text-xs font-medium text-muted-foreground">Suggested</p>
				<p className="text-sm">{after}</p>
			</div>
			<div className="flex justify-end gap-2">
				<Button type="button" variant="outline" size="sm" onClick={onReject}>
					Reject
				</Button>
				<Button type="button" size="sm" onClick={onAccept}>
					Accept
				</Button>
			</div>
		</div>
	);
}
