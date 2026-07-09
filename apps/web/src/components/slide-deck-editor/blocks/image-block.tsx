"use client";

import { useState } from "react";
import type { SlideDeckBlock, SlideDeckMedia } from "@oh-my-class/schemas";
import { Button } from "@/components/ui/button";
import { BLOCK_BODY_MAX, BLOCK_BODY_MIN, MEDIA_ALT_TEXT_MAX, MEDIA_ALT_TEXT_MIN, clampOrReject } from "../block-constraints";
import { EditableText } from "../editable-text";
import { MediaLibraryPicker } from "./media-library-picker";

/** SDE-02 registry: `image` block — `body` is the caption. */
export function applyImageCaptionEdit(block: SlideDeckBlock, draft: string): SlideDeckBlock {
	const result = clampOrReject(draft, BLOCK_BODY_MIN, BLOCK_BODY_MAX);
	return result.ok ? { ...block, body: result.value } : block;
}

/**
 * `image`/`diagram` blocks set `requires_alt_text: true` in BLOCK_REGISTRY —
 * alt text can be edited but never cleared, and there is nothing to edit if
 * the block has no `media` attached (a malformed/legacy artifact).
 */
export function applyImageAltTextEdit(block: SlideDeckBlock, draft: string): SlideDeckBlock {
	if (!block.media) return block;
	const result = clampOrReject(draft, MEDIA_ALT_TEXT_MIN, MEDIA_ALT_TEXT_MAX);
	return result.ok ? { ...block, media: { ...block.media, alt_text: result.value } } : block;
}

/** SDX-02: attach a media asset selected from the teacher's library. */
export function applyMediaSelection(block: SlideDeckBlock, media: SlideDeckMedia): SlideDeckBlock {
	return { ...block, media };
}

export function ImageBlock({
	block,
	onChange,
}: {
	readonly block: SlideDeckBlock;
	readonly onChange: (next: SlideDeckBlock) => void;
}) {
	const [pickerOpen, setPickerOpen] = useState(false);

	return (
		<figure className="space-y-2 rounded-md border border-border bg-card p-3">
			<div
				className="flex h-32 items-center justify-center rounded-md bg-muted text-sm text-muted-foreground"
				aria-hidden="true"
			>
				Image placeholder
			</div>
			<Button type="button" variant="outline" size="sm" onClick={() => setPickerOpen(true)}>
				Choose from library
			</Button>
			{pickerOpen ? (
				<MediaLibraryPicker
					onSelect={(media) => {
						onChange(applyMediaSelection(block, media));
						setPickerOpen(false);
					}}
					onClose={() => setPickerOpen(false)}
				/>
			) : null}
			<figcaption>
				<EditableText
					as="p"
					className="text-sm"
					value={block.body}
					maxLength={BLOCK_BODY_MAX}
					multiline
					ariaLabel="Image caption"
					emptyLabel="Click to add a caption"
					onCommit={(draft) => onChange(applyImageCaptionEdit(block, draft))}
				/>
			</figcaption>
			{block.media ? (
				<div>
					<p className="text-xs font-medium text-muted-foreground">Alt text (required for accessibility)</p>
					<EditableText
						as="span"
						className="block text-sm"
						value={block.media.alt_text}
						maxLength={MEDIA_ALT_TEXT_MAX}
						ariaLabel="Image alt text"
						onCommit={(draft) => onChange(applyImageAltTextEdit(block, draft))}
					/>
				</div>
			) : (
				<p className="text-xs text-destructive">No media attached to this image block — alt text cannot be edited.</p>
			)}
		</figure>
	);
}
