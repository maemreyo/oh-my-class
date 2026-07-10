import type { SlideDeckBlock, SlideDeckData } from "@oh-my-class/schemas";
import { ApiError } from "@/lib/api-client";

/**
 * SDE-07: explicit-commit save against SDE-04's scoped block-edit endpoint
 * (`PATCH .../snapshots/{snapshot_id}/blocks/{block_id}`, see
 * `services/gateway/routers/teaching_pack_previews.py::edit_slide_deck_snapshot_block`).
 *
 * That endpoint edits ONE block's text per call and optimistic-locks on
 * `base_snapshot_id` -- there is no whole-deck/batch write endpoint. So a
 * "Save" click that touched multiple blocks makes one chained call per dirty
 * block (each success's `snapshot_id` becomes the next call's
 * `base_snapshot_id`), not one call for the whole deck. The "exactly one
 * call" AC is about never firing per keystroke/per field-edit -- editing a
 * single block any number of times still yields exactly one call here.
 * ponytail: a true multi-block atomic commit needs a batch endpoint that
 * doesn't exist yet; add one if teachers commonly edit >1 block per save.
 */

export const DECK_SAVE_CONFLICT_MESSAGE = "Someone/something changed this deck. Reload to continue.";

/** Blocks that differ from `original` by *reference* -- valid because every
 * block-edit component here does an immutable `slide.blocks.map(...)`
 * replace (see `slide-canvas.tsx`'s `updateBlock`), so an untouched block
 * keeps the exact same object reference across edits. */
export interface DirtyBlock {
	readonly slideId: string;
	readonly block: SlideDeckBlock;
}

export function diffDirtyBlocks(original: SlideDeckData, current: SlideDeckData): readonly DirtyBlock[] {
	const originalBlocks = new Map<string, SlideDeckBlock>();
	for (const slide of original.slides) {
		for (const block of slide.blocks) originalBlocks.set(block.block_id, block);
	}
	const dirty: DirtyBlock[] = [];
	for (const slide of current.slides) {
		for (const block of slide.blocks) {
			if (originalBlocks.get(block.block_id) !== block) dirty.push({ slideId: slide.slide_id, block });
		}
	}
	return dirty;
}

export interface EditBlockArgs {
	readonly snapshotId: string;
	readonly blockId: string;
	readonly newContent: string;
	/** SDE-08: `"ai_assisted_edit"` for a block whose current body came from
	 * an applied AI rewrite suggestion; omitted (server defaults to
	 * `"teacher_edit"`) for every other edit. */
	readonly authority?: "teacher_edit" | "ai_assisted_edit";
}

export interface EditBlockResult {
	readonly snapshot_id: string;
}

export type EditBlockFn = (args: EditBlockArgs) => Promise<EditBlockResult>;

export interface SaveDeckEditsResult {
	readonly ok: boolean;
	readonly conflict: boolean;
	/** Updated head snapshot id -- unchanged from the input on failure. */
	readonly snapshotId: string;
	readonly error?: string;
	readonly callCount: number;
}

/**
 * Save every dirty block once, chaining `base_snapshot_id` across calls.
 * Stops at the first failure (409 or otherwise) so nothing is saved past a
 * conflict; the caller decides whether to keep/clear the local draft based
 * on `result.ok`.
 */
export async function saveDeckEdits(args: {
	readonly originalDeck: SlideDeckData;
	readonly currentDeck: SlideDeckData;
	readonly baseSnapshotId: string;
	readonly editBlock: EditBlockFn;
	/** SDE-08: block ids whose current body is an applied-but-unsaved AI
	 * rewrite -- those blocks' edit call carries `authority: "ai_assisted_edit"`
	 * instead of the default `"teacher_edit"`. */
	readonly aiAssistedBlockIds?: ReadonlySet<string>;
}): Promise<SaveDeckEditsResult> {
	const dirty = diffDirtyBlocks(args.originalDeck, args.currentDeck);
	let snapshotId = args.baseSnapshotId;
	let callCount = 0;
	for (const { block } of dirty) {
		callCount += 1;
		try {
			const authority = args.aiAssistedBlockIds?.has(block.block_id) ? "ai_assisted_edit" : undefined;
			// eslint-disable-next-line no-await-in-loop -- each call's result (the new snapshot_id) is the next call's input; they are inherently sequential, not parallelizable.
			const response = await args.editBlock({ snapshotId, blockId: block.block_id, newContent: block.body, authority });
			snapshotId = response.snapshot_id;
		} catch (error) {
			if (error instanceof ApiError && error.status === 409) {
				return { ok: false, conflict: true, snapshotId, error: DECK_SAVE_CONFLICT_MESSAGE, callCount };
			}
			const message = error instanceof Error ? error.message : "Could not save this deck. Please try again.";
			return { ok: false, conflict: false, snapshotId, error: message, callCount };
		}
	}
	return { ok: true, conflict: false, snapshotId, callCount };
}
