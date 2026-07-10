"use client";

import { Button } from "@/components/ui/button";

/**
 * SDE-08: the single generic before/after confirmation modal for an
 * AI-assisted block rewrite -- one component reused across every block type
 * (heading, paragraph, callout, image caption, interaction prompt, ...),
 * never a per-block-type variant. Structurally the same before/after +
 * explicit two-button shape as SDX-04's `AiAltTextConfirmModal` (that one
 * stays a separate, narrower component: it confirms a `media.alt_text` field,
 * not a block `body`, and predates this generic one -- see its own doc
 * comment). Rejecting ("Cancel") never touches the caller's block state.
 */
export function AiBlockRewriteConfirmModal({
	blockLabel,
	before,
	after,
	onApply,
	onCancel,
}: {
	/** Short human label for what's being rewritten, e.g. "Paragraph text" or
	 * "Heading" -- lets one modal read sensibly for any block type. */
	readonly blockLabel: string;
	readonly before: string;
	readonly after: string;
	readonly onApply: () => void;
	readonly onCancel: () => void;
}) {
	return (
		<div
			role="dialog"
			aria-label={`Confirm AI rewrite: ${blockLabel}`}
			className="space-y-3 rounded-md border border-border bg-popover p-3 shadow-md"
		>
			<p className="text-sm font-medium">AI-suggested rewrite -- {blockLabel}</p>
			<div>
				<p className="text-xs font-medium text-muted-foreground">Current</p>
				<p className="text-sm">{before || "(empty)"}</p>
			</div>
			<div>
				<p className="text-xs font-medium text-muted-foreground">Suggested</p>
				<p className="text-sm">{after}</p>
			</div>
			<div className="flex justify-end gap-2">
				<Button type="button" variant="outline" size="sm" onClick={onCancel}>
					Cancel
				</Button>
				<Button type="button" size="sm" onClick={onApply}>
					Apply
				</Button>
			</div>
		</div>
	);
}
