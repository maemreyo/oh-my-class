"use client";

import { useState } from "react";
import type { SlideDeckBlock, SlideDeckMedia } from "@oh-my-class/schemas";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { AiAltTextConfirmModal } from "../ai-alt-text-confirm-modal";
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

/** SDX-04: calls the gateway's best-guess alt-text generator for the block's
 * attached media asset (`media_id` doubles as the library `asset_id` — see
 * `buildMediaFromAsset` in `media-library-picker.tsx`), then surfaces the
 * result via the before/after confirmation modal. AI-authored media (SDE-01)
 * already carries a descriptive alt text from the wording LLM call, so this
 * action is only exposed for teacher-uploaded images. */
export async function requestAltTextCandidate(media: SlideDeckMedia): Promise<string> {
	const result = await apiClient.post<{ candidate: string }>(
		`/media-assets/${media.media_id}/generate-alt-text`,
	);
	return result.candidate;
}

/** Persists the accepted text back into the teacher's library (SDX-02's
 * `set_alt_text` "SDX-04 integration point") so re-using this asset in
 * another deck already has real alt text, not just this deck's draft copy.
 * Best-effort: a failure here doesn't block the local draft update, which
 * already happened via `applyImageAltTextEdit`. */
export function persistAltTextToLibrary(mediaId: string, altText: string): void {
	apiClient.put(`/media-assets/${mediaId}/alt-text`, { alt_text: altText }).catch(() => {
		// ponytail: best-effort library sync — the deck draft already has the
		// accepted text either way, so a failed sync here is silent.
	});
}

export function ImageBlock({
	block,
	onChange,
}: {
	readonly block: SlideDeckBlock;
	readonly onChange: (next: SlideDeckBlock) => void;
}) {
	const [pickerOpen, setPickerOpen] = useState(false);
	const [altTextCandidate, setAltTextCandidate] = useState<string | null>(null);
	const [altTextError, setAltTextError] = useState<string | null>(null);
	const [generatingAltText, setGeneratingAltText] = useState(false);

	async function handleGenerateAltText() {
		if (!block.media) return;
		setGeneratingAltText(true);
		setAltTextError(null);
		try {
			setAltTextCandidate(await requestAltTextCandidate(block.media));
		} catch (err) {
			setAltTextError(err instanceof Error ? err.message : "Failed to generate alt text");
		} finally {
			setGeneratingAltText(false);
		}
	}

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
				<div className="space-y-1">
					<p className="text-xs font-medium text-muted-foreground">Alt text (required for accessibility)</p>
					<EditableText
						as="span"
						className="block text-sm"
						value={block.media.alt_text}
						maxLength={MEDIA_ALT_TEXT_MAX}
						ariaLabel="Image alt text"
						onCommit={(draft) => onChange(applyImageAltTextEdit(block, draft))}
					/>
					<Button
						type="button"
						variant="outline"
						size="sm"
						disabled={generatingAltText}
						onClick={handleGenerateAltText}
					>
						{generatingAltText ? "Đang tạo…" : "Tạo alt-text bằng AI"}
					</Button>
					{altTextError ? <p className="text-xs text-destructive">{altTextError}</p> : null}
					{altTextCandidate !== null ? (
						<AiAltTextConfirmModal
							before={block.media.alt_text}
							after={altTextCandidate}
							onAccept={() => {
								onChange(applyImageAltTextEdit(block, altTextCandidate));
								persistAltTextToLibrary(block.media!.media_id, altTextCandidate);
								setAltTextCandidate(null);
							}}
							onReject={() => setAltTextCandidate(null)}
						/>
					) : null}
				</div>
			) : (
				<p className="text-xs text-destructive">No media attached to this image block — alt text cannot be edited.</p>
			)}
		</figure>
	);
}
