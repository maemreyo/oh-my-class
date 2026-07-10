import type { SlideDeckData } from "@oh-my-class/schemas";

/**
 * SDE-07: crash-recovery draft persistence for the deck editor.
 *
 * Namespacing mirrors SDH-03's precedent in
 * `packages/renderer/templates/pages/slide_deck.html` (`omc:slide-deck:{deckId}:prefs`)
 * -- same `omc:<feature>:{id}:<kind>` shape, same try/catch-and-degrade
 * behavior for `file://`/private-mode/storage-disabled contexts. That file is
 * vanilla JS against `window.localStorage` directly; this is the React-side
 * equivalent, so it takes a `Storage`-shaped param instead of touching
 * `window` itself -- keeps it usable in tests and SSR without a DOM.
 */

/** Minimal shape of `window.localStorage` this module needs -- lets tests
 * pass an in-memory fake instead of requiring a jsdom environment. */
export interface DraftStorage {
	getItem(key: string): string | null;
	setItem(key: string, value: string): void;
	removeItem(key: string): void;
}

export function deckDraftStorageKey(deckId: string): string {
	return `omc:deck-editor:${deckId}:draft`;
}

export function readDeckDraft(storage: DraftStorage, deckId: string): SlideDeckData | null {
	try {
		const raw = storage.getItem(deckDraftStorageKey(deckId));
		return raw ? (JSON.parse(raw) as SlideDeckData) : null;
	} catch {
		return null; // storage disabled, or a corrupt/foreign value -- degrade to "no draft".
	}
}

export function writeDeckDraft(storage: DraftStorage, deckId: string, deck: SlideDeckData): void {
	try {
		storage.setItem(deckDraftStorageKey(deckId), JSON.stringify(deck));
	} catch {
		// ponytail: storage unavailable (private mode, quota, file://) -- in-memory
		// edit state still works for this page view, same tradeoff as SDH-03.
	}
}

export function clearDeckDraft(storage: DraftStorage, deckId: string): void {
	try {
		storage.removeItem(deckDraftStorageKey(deckId));
	} catch {
		// ponytail: same degrade-gracefully rationale as writeDeckDraft.
	}
}
