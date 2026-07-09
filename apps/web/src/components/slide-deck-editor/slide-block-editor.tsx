"use client";

import type { ComponentType } from "react";
import type { SlideDeckBlock } from "@oh-my-class/schemas";
import { CalloutBlock } from "./blocks/callout-block";
import { HeadingBlock } from "./blocks/heading-block";
import { ImageBlock } from "./blocks/image-block";
import { InteractionPromptBlock } from "./blocks/interaction-prompt-block";
import { ParagraphBlock } from "./blocks/paragraph-block";

type BlockComponent = ComponentType<{ block: SlideDeckBlock; onChange: (next: SlideDeckBlock) => void }>;

// SDE-03 scoping: only block types actually emitted by the 5
// renderer-supported layouts (title, content, question, activity, summary —
// see RENDERER_SUPPORTED_SLIDE_LAYOUTS in slide-deck-projection.ts) get an
// edit component. `diagram` is declared in BLOCK_REGISTRY but never emitted
// by those layouts today; add its editor when a supported layout starts
// using it.
const BLOCK_COMPONENTS: Partial<Record<SlideDeckBlock["block_type"], BlockComponent>> = {
	heading: HeadingBlock,
	paragraph: ParagraphBlock,
	callout: CalloutBlock,
	image: ImageBlock,
	interaction_prompt: InteractionPromptBlock,
};

export function SlideBlockEditor({
	block,
	onChange,
}: {
	readonly block: SlideDeckBlock;
	readonly onChange: (next: SlideDeckBlock) => void;
}) {
	const Component = BLOCK_COMPONENTS[block.block_type];
	if (!Component) {
		return (
			<div className="rounded-md border border-dashed border-muted-foreground/40 p-3 text-sm text-muted-foreground">
				Block type &quot;{block.block_type}&quot; has no editor yet.
			</div>
		);
	}
	return <Component block={block} onChange={onChange} />;
}
