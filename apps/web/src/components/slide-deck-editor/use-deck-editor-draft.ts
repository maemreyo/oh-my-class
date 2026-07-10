"use client";

import { useEffect, useState } from "react";
import type { SlideDeckData } from "@oh-my-class/schemas";
import { clearDeckDraft, readDeckDraft, writeDeckDraft } from "./deck-draft-store";

/**
 * SDE-07: local-draft buffer for the deck editor. Thin React wrapper around
 * `deck-draft-store.ts`'s framework-free read/write/clear -- keep new logic
 * in that module (or `deck-save.ts`/`deck-navigate-away.ts`) so it stays
 * unit-testable without a DOM; this hook only wires it to component state.
 */
export function useDeckEditorDraft(deckId: string, initialDeck: SlideDeckData) {
	const [deck, setDeckState] = useState<SlideDeckData>(initialDeck);
	const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

	// Crash recovery: on mount (or if the route swaps decks), restore any
	// draft left over from a previous tab session for this deck.
	useEffect(() => {
		if (typeof window === "undefined") return;
		const restored = readDeckDraft(window.localStorage, deckId);
		if (restored) {
			setDeckState(restored);
			setHasUnsavedChanges(true);
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally only on deckId change, not initialDeck (a fresh server fetch must not clobber a just-restored draft).
	}, [deckId]);

	function updateDeck(updater: (previous: SlideDeckData) => SlideDeckData): void {
		setDeckState((previous) => {
			const next = updater(previous);
			setHasUnsavedChanges(true);
			if (typeof window !== "undefined") writeDeckDraft(window.localStorage, deckId, next);
			return next;
		});
	}

	function clearDraft(): void {
		setHasUnsavedChanges(false);
		if (typeof window !== "undefined") clearDeckDraft(window.localStorage, deckId);
	}

	return { deck, updateDeck, hasUnsavedChanges, clearDraft } as const;
}
