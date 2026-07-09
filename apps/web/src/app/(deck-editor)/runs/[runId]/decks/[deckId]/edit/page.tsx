"use client";

import { useMemo } from "react";
import { useParams } from "next/navigation";
import type { SlideDeckData } from "@oh-my-class/schemas";
import { SlideDeckEditor } from "@/components/slide-deck-editor/deck-editor";
import { useArtifact } from "@/hooks/use-artifact";

export default function SlideDeckEditPage() {
	const params = useParams();
	const runId = params.runId as string;
	const deckId = params.deckId as string;

	const { data: artifact, isLoading, error } = useArtifact(runId, deckId);
	const deck = useMemo(() => extractSlideDeck(artifact), [artifact]);

	if (isLoading) return <FullScreenMessage>Loading slide deck...</FullScreenMessage>;
	if (error) return <FullScreenMessage>Could not load run {runId}: {error.message}</FullScreenMessage>;
	if (!deck) return <FullScreenMessage>No slide deck data found for artifact {deckId}.</FullScreenMessage>;

	return <SlideDeckEditor initialDeck={deck} />;
}

/**
 * The gateway returns the raw artifact dict `build_slide_deck_artifact`
 * produces — the deck lives at `metadata.slide_deck_data` (and is mirrored
 * into `sections[0].slide_deck`); see slide_deck_artifact.py.
 *
 * This is a hand-rolled structural guard (same scope/style as
 * `isSlideDeckData` in teaching-packs-slide-deck-preview.tsx) rather than
 * `SlideDeckDataSchema.safeParse` — @oh-my-class/schemas ships its TS source
 * directly, and Turbopack can't bundle a *value* import of it for the
 * browser (see block-constraints.ts for the full explanation). It only
 * checks the fields this editor actually reads; `SlideDeckData`'s other
 * fields (accessibility, media_policy, surfaces, ...) are trusted from the
 * type predicate, same as the existing preview component.
 */
function extractSlideDeck(artifact: unknown): SlideDeckData | null {
	if (!isRecord(artifact)) return null;
	const metadata = isRecord(artifact.metadata) ? artifact.metadata : null;
	const candidates: unknown[] = [metadata?.slide_deck_data, firstSectionDeck(artifact.sections)];
	for (const candidate of candidates) {
		if (isSlideDeckData(candidate)) return candidate;
	}
	return null;
}

function firstSectionDeck(sections: unknown): unknown {
	if (!Array.isArray(sections) || sections.length === 0) return null;
	const first: unknown = sections[0];
	return isRecord(first) ? first.slide_deck : null;
}

function isSlideDeckData(value: unknown): value is SlideDeckData {
	return isRecord(value) && typeof value.deck_id === "string" && typeof value.title === "string" && Array.isArray(value.slides) && value.slides.every(isSlideDeckSlide);
}

function isSlideDeckSlide(value: unknown): boolean {
	return (
		isRecord(value) &&
		typeof value.slide_id === "string" &&
		typeof value.title === "string" &&
		typeof value.layout === "string" &&
		Array.isArray(value.blocks) &&
		value.blocks.every(isSlideDeckBlock) &&
		(value.interactions === undefined || (Array.isArray(value.interactions) && value.interactions.every(isSlideDeckInteraction)))
	);
}

function isSlideDeckBlock(value: unknown): boolean {
	return isRecord(value) && typeof value.block_id === "string" && typeof value.block_type === "string" && typeof value.body === "string";
}

function isSlideDeckInteraction(value: unknown): boolean {
	return isRecord(value) && typeof value.interaction_id === "string" && typeof value.interaction_type === "string" && typeof value.prompt === "string";
}

function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function FullScreenMessage({ children }: { readonly children: React.ReactNode }) {
	return <div className="flex h-full items-center justify-center p-8 text-sm text-muted-foreground">{children}</div>;
}
