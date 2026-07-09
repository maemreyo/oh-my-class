"use client";

import type { SlideDeckBlock } from "@oh-my-class/schemas";
import { BLOCK_BODY_MAX, BLOCK_BODY_MIN, clampOrReject } from "../block-constraints";
import { EditableText } from "../editable-text";

/** SDE-02 registry: `paragraph` block — `body` is the only editable field. */
export function applyParagraphEdit(block: SlideDeckBlock, draft: string): SlideDeckBlock {
	const result = clampOrReject(draft, BLOCK_BODY_MIN, BLOCK_BODY_MAX);
	return result.ok ? { ...block, body: result.value } : block;
}

export function ParagraphBlock({
	block,
	onChange,
}: {
	readonly block: SlideDeckBlock;
	readonly onChange: (next: SlideDeckBlock) => void;
}) {
	return (
		<EditableText
			as="p"
			className="text-base leading-relaxed"
			value={block.body}
			maxLength={BLOCK_BODY_MAX}
			multiline
			ariaLabel="Paragraph text"
			onCommit={(draft) => onChange(applyParagraphEdit(block, draft))}
		/>
	);
}
