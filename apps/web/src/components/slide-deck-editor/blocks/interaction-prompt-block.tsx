"use client";

import type { SlideDeckBlock } from "@oh-my-class/schemas";
import { BLOCK_BODY_MAX, BLOCK_BODY_MIN, clampOrReject } from "../block-constraints";
import { EditableText } from "../editable-text";

/** SDE-02 registry: `interaction_prompt` block — `body` is the only editable field. */
export function applyInteractionPromptEdit(block: SlideDeckBlock, draft: string): SlideDeckBlock {
	const result = clampOrReject(draft, BLOCK_BODY_MIN, BLOCK_BODY_MAX);
	return result.ok ? { ...block, body: result.value } : block;
}

export function InteractionPromptBlock({
	block,
	onChange,
}: {
	readonly block: SlideDeckBlock;
	readonly onChange: (next: SlideDeckBlock) => void;
}) {
	return (
		<div className="rounded-md border border-dashed border-primary/50 bg-primary/5 p-3">
			<EditableText
				as="p"
				className="text-sm font-medium italic"
				value={block.body}
				maxLength={BLOCK_BODY_MAX}
				multiline
				ariaLabel="Interaction prompt text"
				onCommit={(draft) => onChange(applyInteractionPromptEdit(block, draft))}
			/>
		</div>
	);
}
