import { SlideDeckDataSchema, type SlideDeckData } from "@oh-my-class/schemas";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-client";
import { DECK_SAVE_CONFLICT_MESSAGE, diffDirtyBlocks, saveDeckEdits } from "./deck-save";

function makeDeck(blockBodies: readonly string[]): SlideDeckData {
	return SlideDeckDataSchema.parse({
		deck_id: "deck-1",
		title: "Photosynthesis",
		locale: "en-US",
		surfaces: {
			student: { mode: "presentation", export_format: "html" },
			teacher: { mode: "teacher_guide", export_format: "html" },
			print: { mode: "print", export_format: "html" },
		},
		slides: [
			{
				slide_id: "slide-1",
				title: "Slide 1",
				layout: "content",
				progression: { step_index: 1, reveal_policy: "all_at_once" },
				blocks: blockBodies.map((body, index) => ({ block_id: `block-${index}`, block_type: "paragraph", body })),
			},
		],
		accessibility: { reading_level: "grade_6", language: "en-US", alt_text_required: true, keyboard_navigation: true },
		media_policy: { default_tier: "packaged", online_optional_allowed: false, fallback_required: true },
	});
}

describe("diffDirtyBlocks", () => {
	it("finds no dirty blocks when nothing changed", () => {
		const deck = makeDeck(["a", "b"]);
		expect(diffDirtyBlocks(deck, deck)).toEqual([]);
	});

	it("finds only the block whose reference changed, regardless of how many times it was edited", () => {
		const original = makeDeck(["a", "b"]);
		// Simulate several keystrokes on block-0 collapsing into one final edit,
		// via the same immutable-replace pattern slide-canvas.tsx's updateBlock uses.
		let current = original;
		for (const next of ["a1", "a12", "a123"]) {
			current = {
				...current,
				slides: current.slides.map((slide) => ({
					...slide,
					blocks: slide.blocks.map((block) => (block.block_id === "block-0" ? { ...block, body: next } : block)),
				})),
			};
		}
		const dirty = diffDirtyBlocks(original, current);
		expect(dirty).toHaveLength(1);
		expect(dirty[0]?.block.block_id).toBe("block-0");
		expect(dirty[0]?.block.body).toBe("a123");
	});

	it("finds every block that changed when more than one was edited", () => {
		const original = makeDeck(["a", "b"]);
		const current: SlideDeckData = {
			...original,
			slides: original.slides.map((slide) => ({
				...slide,
				blocks: slide.blocks.map((block) => ({ ...block, body: `${block.body}!` })),
			})),
		};
		expect(diffDirtyBlocks(original, current).map((d) => d.block.block_id)).toEqual(["block-0", "block-1"]);
	});
});

describe("saveDeckEdits", () => {
	it("makes exactly one network call when a single block was edited any number of times", async () => {
		const original = makeDeck(["a", "b"]);
		const current: SlideDeckData = {
			...original,
			slides: original.slides.map((slide) => ({
				...slide,
				blocks: slide.blocks.map((block) => (block.block_id === "block-0" ? { ...block, body: "edited" } : block)),
			})),
		};
		const editBlock = vi.fn().mockResolvedValue({ snapshot_id: "snapshot-2" });

		const result = await saveDeckEdits({ originalDeck: original, currentDeck: current, baseSnapshotId: "snapshot-1", editBlock });

		expect(editBlock).toHaveBeenCalledTimes(1);
		expect(editBlock).toHaveBeenCalledWith({ snapshotId: "snapshot-1", blockId: "block-0", newContent: "edited" });
		expect(result).toEqual({ ok: true, conflict: false, snapshotId: "snapshot-2", callCount: 1 });
	});

	it("is a no-op (zero calls) when nothing is dirty", async () => {
		const deck = makeDeck(["a", "b"]);
		const editBlock = vi.fn();

		const result = await saveDeckEdits({ originalDeck: deck, currentDeck: deck, baseSnapshotId: "snapshot-1", editBlock });

		expect(editBlock).not.toHaveBeenCalled();
		expect(result).toEqual({ ok: true, conflict: false, snapshotId: "snapshot-1", callCount: 0 });
	});

	it("chains base_snapshot_id across multiple dirty blocks (one call per block, not one for the whole deck)", async () => {
		const original = makeDeck(["a", "b"]);
		const current: SlideDeckData = {
			...original,
			slides: original.slides.map((slide) => ({
				...slide,
				blocks: slide.blocks.map((block) => ({ ...block, body: `${block.body}!` })),
			})),
		};
		const editBlock = vi
			.fn()
			.mockResolvedValueOnce({ snapshot_id: "snapshot-2" })
			.mockResolvedValueOnce({ snapshot_id: "snapshot-3" });

		const result = await saveDeckEdits({ originalDeck: original, currentDeck: current, baseSnapshotId: "snapshot-1", editBlock });

		expect(editBlock).toHaveBeenCalledTimes(2);
		expect(editBlock).toHaveBeenNthCalledWith(1, { snapshotId: "snapshot-1", blockId: "block-0", newContent: "a!" });
		expect(editBlock).toHaveBeenNthCalledWith(2, { snapshotId: "snapshot-2", blockId: "block-1", newContent: "b!" });
		expect(result.snapshotId).toBe("snapshot-3");
		expect(result.ok).toBe(true);
	});

	it("surfaces the teacher-safe conflict message on a 409 and keeps the reported snapshotId at its pre-conflict value", async () => {
		const original = makeDeck(["a"]);
		const current: SlideDeckData = {
			...original,
			slides: original.slides.map((slide) => ({ ...slide, blocks: slide.blocks.map((block) => ({ ...block, body: "edited" })) })),
		};
		const editBlock = vi.fn().mockRejectedValue(new ApiError("base_snapshot_id_stale", 409));

		const result = await saveDeckEdits({ originalDeck: original, currentDeck: current, baseSnapshotId: "snapshot-1", editBlock });

		expect(result.ok).toBe(false);
		expect(result.conflict).toBe(true);
		expect(result.error).toBe(DECK_SAVE_CONFLICT_MESSAGE);
		expect(result.error).not.toMatch(/base_snapshot_id_stale/); // never the raw backend detail
	});

	it("tags a saved block's edit call with ai_assisted_edit authority when it's in aiAssistedBlockIds (SDE-08)", async () => {
		const original = makeDeck(["a", "b"]);
		const current: SlideDeckData = {
			...original,
			slides: original.slides.map((slide) => ({
				...slide,
				blocks: slide.blocks.map((block) => ({ ...block, body: `${block.body}!` })),
			})),
		};
		const editBlock = vi
			.fn()
			.mockResolvedValueOnce({ snapshot_id: "snapshot-2" })
			.mockResolvedValueOnce({ snapshot_id: "snapshot-3" });

		await saveDeckEdits({
			originalDeck: original,
			currentDeck: current,
			baseSnapshotId: "snapshot-1",
			editBlock,
			aiAssistedBlockIds: new Set(["block-0"]),
		});

		expect(editBlock).toHaveBeenNthCalledWith(1, { snapshotId: "snapshot-1", blockId: "block-0", newContent: "a!", authority: "ai_assisted_edit" });
		expect(editBlock).toHaveBeenNthCalledWith(2, { snapshotId: "snapshot-2", blockId: "block-1", newContent: "b!", authority: undefined });
	});

	it("surfaces a generic (non-conflict) error for any other failure", async () => {
		const original = makeDeck(["a"]);
		const current: SlideDeckData = {
			...original,
			slides: original.slides.map((slide) => ({ ...slide, blocks: slide.blocks.map((block) => ({ ...block, body: "edited" })) })),
		};
		const editBlock = vi.fn().mockRejectedValue(new ApiError("not_a_slide_deck", 422));

		const result = await saveDeckEdits({ originalDeck: original, currentDeck: current, baseSnapshotId: "snapshot-1", editBlock });

		expect(result.ok).toBe(false);
		expect(result.conflict).toBe(false);
		expect(result.error).toBeTruthy();
	});
});
