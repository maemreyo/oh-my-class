"use client";

import type { SlideDeckBlock } from "@oh-my-class/schemas";
import { BLOCK_BODY_MAX, BLOCK_BODY_MIN, clampOrReject } from "../block-constraints";
import { EditableText } from "../editable-text";

/** SDE-02 registry: `heading` block — `body` is the only editable field. */
export function applyHeadingEdit(block: SlideDeckBlock, draft: string): SlideDeckBlock {
	const result = clampOrReject(draft, BLOCK_BODY_MIN, BLOCK_BODY_MAX);
	return result.ok ? { ...block, body: result.value } : block;
}

export function HeadingBlock({
	block,
	onChange,
}: {
	readonly block: SlideDeckBlock;
	readonly onChange: (next: SlideDeckBlock) => void;
}) {
	return (
		<EditableText
			as="h2"
			className="text-2xl font-bold tracking-tight"
			value={block.body}
			maxLength={BLOCK_BODY_MAX}
			ariaLabel="Slide heading"
			onCommit={(draft) => onChange(applyHeadingEdit(block, draft))}
		/>
	);
}
