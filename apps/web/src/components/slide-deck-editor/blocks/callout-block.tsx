"use client";

import type { SlideDeckBlock } from "@oh-my-class/schemas";
import { BLOCK_BODY_MAX, BLOCK_BODY_MIN, clampOrReject } from "../block-constraints";
import { EditableText } from "../editable-text";

/** SDE-02 registry: `callout` block — `body` is the only editable field. */
export function applyCalloutEdit(block: SlideDeckBlock, draft: string): SlideDeckBlock {
	const result = clampOrReject(draft, BLOCK_BODY_MIN, BLOCK_BODY_MAX);
	return result.ok ? { ...block, body: result.value } : block;
}

export function CalloutBlock({
	block,
	onChange,
}: {
	readonly block: SlideDeckBlock;
	readonly onChange: (next: SlideDeckBlock) => void;
}) {
	return (
		<div className="rounded-md border-l-4 border-primary bg-muted p-3">
			<EditableText
				as="p"
				className="text-sm font-medium"
				value={block.body}
				maxLength={BLOCK_BODY_MAX}
				multiline
				ariaLabel="Callout text"
				onCommit={(draft) => onChange(applyCalloutEdit(block, draft))}
			/>
		</div>
	);
}
