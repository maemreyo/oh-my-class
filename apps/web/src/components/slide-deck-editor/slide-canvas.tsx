"use client";

import type { SlideDeckBlock, SlideDeckInteraction, SlideDeckSlide } from "@oh-my-class/schemas";
import { QuickCheckInteraction } from "./quick-check-interaction";
import { SlideBlockEditor } from "./slide-block-editor";

// SDE-03 scoping: `quick_check`/`multiple_choice_single` are the only
// interaction types the 5 renderer-supported layouts currently emit (see
// `_practice_slide` in content_materialization.py) and share an identical
// shape, so one component covers both. Every other declared interaction
// type (poll, timer, discussion_prompt, ...) has no edit UI yet.
const CHOICE_INTERACTION_TYPES = new Set<SlideDeckInteraction["interaction_type"]>(["quick_check", "multiple_choice_single"]);

export function SlideCanvas({
	slide,
	onSlideChange,
}: {
	readonly slide: SlideDeckSlide;
	readonly onSlideChange: (next: SlideDeckSlide) => void;
}) {
	function updateBlock(updated: SlideDeckBlock) {
		onSlideChange({ ...slide, blocks: slide.blocks.map((block) => (block.block_id === updated.block_id ? updated : block)) });
	}

	function updateInteraction(updated: SlideDeckInteraction) {
		onSlideChange({
			...slide,
			interactions: (slide.interactions ?? []).map((interaction) =>
				interaction.interaction_id === updated.interaction_id ? updated : interaction,
			),
		});
	}

	return (
		<div className="space-y-4 rounded-lg border border-border bg-background p-6 shadow-sm">
			<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{slide.layout} layout</p>
			<div className="space-y-3">
				{slide.blocks.map((block) => (
					<SlideBlockEditor key={block.block_id} block={block} onChange={updateBlock} />
				))}
			</div>
			{(slide.interactions ?? []).length > 0 ? (
				<div className="space-y-3">
					{(slide.interactions ?? []).map((interaction) =>
						CHOICE_INTERACTION_TYPES.has(interaction.interaction_type) ? (
							<QuickCheckInteraction key={interaction.interaction_id} interaction={interaction} onChange={updateInteraction} />
						) : (
							<div
								key={interaction.interaction_id}
								className="rounded-md border border-dashed border-muted-foreground/40 p-3 text-sm text-muted-foreground"
							>
								Interaction type &quot;{interaction.interaction_type}&quot; has no editor yet.
							</div>
						),
					)}
				</div>
			) : null}
		</div>
	);
}
