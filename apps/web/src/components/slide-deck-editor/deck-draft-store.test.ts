import { SlideDeckDataSchema } from "@oh-my-class/schemas";
import { describe, expect, it } from "vitest";
import { clearDeckDraft, deckDraftStorageKey, readDeckDraft, writeDeckDraft, type DraftStorage } from "./deck-draft-store";

const deck = SlideDeckDataSchema.parse({
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
			blocks: [{ block_id: "block-0", block_type: "paragraph", body: "Hello" }],
		},
	],
	accessibility: { reading_level: "grade_6", language: "en-US", alt_text_required: true, keyboard_navigation: true },
	media_policy: { default_tier: "packaged", online_optional_allowed: false, fallback_required: true },
});

/** In-memory fake so this runs without jsdom/`localStorage` (vitest.config.ts uses environment: "node"). */
function fakeStorage(): DraftStorage {
	const backing = new Map<string, string>();
	return {
		getItem: (key) => backing.get(key) ?? null,
		setItem: (key, value) => void backing.set(key, value),
		removeItem: (key) => void backing.delete(key),
	};
}

describe("deck draft store — SDE-07 crash-recovery persistence", () => {
	it("namespaces the storage key like SDH-03's omc:<feature>:{id}:<kind> convention", () => {
		expect(deckDraftStorageKey("deck-1")).toBe("omc:deck-editor:deck-1:draft");
	});

	it("round-trips a draft through write -> read (simulated reload)", () => {
		const storage = fakeStorage();
		writeDeckDraft(storage, "deck-1", deck);
		expect(readDeckDraft(storage, "deck-1")).toEqual(deck);
	});

	it("returns null when no draft was ever written", () => {
		expect(readDeckDraft(fakeStorage(), "deck-1")).toBeNull();
	});

	it("clears the draft so a later read returns null", () => {
		const storage = fakeStorage();
		writeDeckDraft(storage, "deck-1", deck);
		clearDeckDraft(storage, "deck-1");
		expect(readDeckDraft(storage, "deck-1")).toBeNull();
	});

	it("degrades to null instead of throwing when storage is disabled", () => {
		const throwingStorage: DraftStorage = {
			getItem: () => {
				throw new Error("storage disabled");
			},
			setItem: () => {
				throw new Error("storage disabled");
			},
			removeItem: () => {
				throw new Error("storage disabled");
			},
		};
		expect(() => writeDeckDraft(throwingStorage, "deck-1", deck)).not.toThrow();
		expect(readDeckDraft(throwingStorage, "deck-1")).toBeNull();
		expect(() => clearDeckDraft(throwingStorage, "deck-1")).not.toThrow();
	});

	it("degrades to null on a corrupt/foreign stored value instead of throwing", () => {
		const storage = fakeStorage();
		storage.setItem(deckDraftStorageKey("deck-1"), "{not json");
		expect(readDeckDraft(storage, "deck-1")).toBeNull();
	});
});
