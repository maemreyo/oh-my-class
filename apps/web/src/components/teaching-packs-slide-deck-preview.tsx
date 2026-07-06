"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { snapshotPreviewUrl } from "@/hooks/use-teaching-packs";
import type { TeachingPackEventPayload } from "@/hooks/use-teaching-packs";

type SlideDeckSurface = "student" | "teacher" | "print";
type FeedbackScope = "deck" | "slide" | "block" | "interaction";

type SlideDeckBlock = Readonly<{
	block_id: string;
	body: string;
	media?: Readonly<{ requires_network?: boolean; fallback_text?: string | null }> | null;
}>;

type SlideDeckInteraction = Readonly<{
	interaction_id: string;
	prompt: string;
	teacher_only?: Readonly<{ rationale?: string; correct_option_ids?: readonly string[] }> | null;
}>;

type SlideDeckSlide = Readonly<{
	slide_id: string;
	title: string;
	blocks: readonly SlideDeckBlock[];
	interactions?: readonly SlideDeckInteraction[];
	teacher_notes?: Readonly<{ facilitation_notes?: readonly string[]; answer_key_notes?: readonly string[] }> | null;
}>;

type SlideDeckData = Readonly<{
	deck_id: string;
	title: string;
	slides: readonly SlideDeckSlide[];
}>;

export type SlideDeckScopedFeedback = Readonly<{
	scope: FeedbackScope;
	deck_id: string;
	slide_id?: string;
	block_id?: string;
	interaction_id?: string;
	reason: string;
}>;

export function hasSlideDeckArtifact(event: TeachingPackEventPayload): boolean {
	const statuses = [...(event.artifact_statuses ?? []), ...(event.artifacts ?? [])];
	return statuses.some((artifact) => artifact.artifact_type === "slide_deck") || slideDeckFromEvent(event) !== null;
}

export function slideDeckFromEvent(event: TeachingPackEventPayload): SlideDeckData | null {
	const candidates = [event["slide_deck_data"], event["slide_deck"], ...artifactPayloads(event)];
	for (const candidate of candidates) {
		const deck = parseSlideDeck(candidate);
		if (deck) return deck;
	}
	return null;
}

export function onlineMediaWarnings(deck: SlideDeckData | null): readonly string[] {
	if (!deck) return [];
	return deck.slides.flatMap((slide) =>
		slide.blocks
			.filter((block) => block.media?.requires_network === true)
			.map((block) => `${slide.title}: ${block.media?.fallback_text ?? "Online media needs a fallback."}`),
	);
}

export function createScopedFeedbackPayload(deck: SlideDeckData, slide: SlideDeckSlide | null, scope: FeedbackScope, reason: string): SlideDeckScopedFeedback {
	const selectedBlock = slide?.blocks[0];
	const selectedInteraction = slide?.interactions?.[0];
	return {
		scope,
		deck_id: deck.deck_id,
		slide_id: scope === "deck" ? undefined : slide?.slide_id,
		block_id: scope === "block" ? selectedBlock?.block_id : undefined,
		interaction_id: scope === "interaction" ? selectedInteraction?.interaction_id : undefined,
		reason: reason.trim(),
	};
}

export function TeachingPacksSlideDeckPreview({ runId, event, onSubmitFeedbackAction }: {
	readonly runId: string;
	readonly event: TeachingPackEventPayload;
	readonly onSubmitFeedbackAction?: (feedback: SlideDeckScopedFeedback) => Promise<void> | void;
}) {
	const deck = useMemo(() => slideDeckFromEvent(event), [event]);
	const snapshotId = event.snapshot_ids?.[0] ?? "";
	const [surface, setSurface] = useState<SlideDeckSurface>("student");
	const [slideIndex, setSlideIndex] = useState(0);
	const [feedbackScope, setFeedbackScope] = useState<FeedbackScope>("slide");
	const [feedback, setFeedback] = useState("");
	if (!hasSlideDeckArtifact(event)) return null;

	const slides = deck?.slides ?? [];
	const currentSlide = slides[slideIndex] ?? null;
	const warnings = onlineMediaWarnings(deck);
	const canSubmitFeedback = deck !== null && feedback.trim().length > 0;

	return (
		<section className="rounded-lg border border-border bg-background p-4" aria-labelledby="slide-deck-preview-title">
			<div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
				<div>
					<p className="text-xs font-semibold uppercase tracking-wide text-primary">Slide-native review</p>
					<h3 id="slide-deck-preview-title" className="text-lg font-semibold">{deck?.title ?? "Slide deck preview"}</h3>
					<p className="mt-1 text-sm text-muted-foreground">Review the same snapshot as a presentation, teacher guide, or print handout.</p>
				</div>
				<SurfaceToggle value={surface} onChange={setSurface} />
			</div>

			<div className="mt-4 grid gap-4 lg:grid-cols-[14rem_minmax(0,1fr)_18rem]">
				<SlideOutline slides={slides} activeIndex={slideIndex} onSelect={setSlideIndex} />
				<div className="space-y-3">
					<SlidePosition slide={currentSlide} index={slideIndex} total={slides.length} />
					{snapshotId ? (
						<iframe
							key={`${snapshotId}-${surface}`}
							title={`Slide deck ${surface} preview`}
							src={snapshotPreviewUrl(runId, snapshotId, surface)}
							className="h-96 w-full rounded-md border border-border bg-card"
							sandbox="allow-same-origin"
						/>
					) : (
						<div className="rounded-md border border-border bg-muted p-6 text-sm text-muted-foreground">Preview snapshot is not ready yet.</div>
					)}
				</div>
				<aside className="space-y-3">
					<TeacherNotesPanel surface={surface} slide={currentSlide} />
					<OnlineMediaPanel warnings={warnings} />
					{deck ? <ScopedFeedbackPanel scope={feedbackScope} feedback={feedback} onScopeChange={setFeedbackScope} onFeedbackChange={setFeedback} onSubmit={() => onSubmitFeedbackAction?.(createScopedFeedbackPayload(deck, currentSlide, feedbackScope, feedback))} disabled={!canSubmitFeedback} /> : null}
				</aside>
			</div>
		</section>
	);
}

function SurfaceToggle({ value, onChange }: { readonly value: SlideDeckSurface; readonly onChange: (surface: SlideDeckSurface) => void }) {
	return <div className="inline-flex rounded-md border border-border bg-card p-1" aria-label="Slide deck preview surface">{(["student", "teacher", "print"] as const).map((surface) => <button key={surface} type="button" className={surface === value ? "rounded bg-primary px-3 py-1 text-sm text-primary-foreground" : "px-3 py-1 text-sm text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"} onClick={() => onChange(surface)}>{surface === "student" ? "Student" : surface === "teacher" ? "Teacher" : "Print"}</button>)}</div>;
}

function SlideOutline({ slides, activeIndex, onSelect }: { readonly slides: readonly SlideDeckSlide[]; readonly activeIndex: number; readonly onSelect: (index: number) => void }) {
	if (slides.length === 0) return <div className="rounded-md border border-border bg-muted p-3 text-sm text-muted-foreground">Slide outline will appear when deck metadata is available.</div>;
	return <nav aria-label="Slide outline" className="space-y-2">{slides.map((slide, index) => <button key={slide.slide_id} type="button" className={index === activeIndex ? "w-full rounded-md border border-primary bg-muted p-3 text-left text-sm" : "w-full rounded-md border border-border bg-card p-3 text-left text-sm hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"} onClick={() => onSelect(index)}><span className="block text-xs font-medium text-muted-foreground">Slide {index + 1}</span><span className="mt-1 block font-medium">{slide.title}</span></button>)}</nav>;
}

function SlidePosition({ slide, index, total }: { readonly slide: SlideDeckSlide | null; readonly index: number; readonly total: number }) {
	return <div className="flex items-center justify-between rounded-md border border-border bg-card px-3 py-2 text-sm"><span className="font-medium">{slide?.title ?? "Deck preview"}</span><span className="text-muted-foreground">{total > 0 ? `${index + 1} / ${total}` : "No slide metadata"}</span></div>;
}

function TeacherNotesPanel({ surface, slide }: { readonly surface: SlideDeckSurface; readonly slide: SlideDeckSlide | null }) {
	const notes = surface === "teacher" ? slide?.teacher_notes?.facilitation_notes ?? [] : [];
	const answers = surface === "teacher" ? slide?.teacher_notes?.answer_key_notes ?? [] : [];
	return <div className="rounded-md border border-border bg-card p-3"><p className="text-sm font-medium">Teacher notes</p>{surface !== "teacher" ? <p className="mt-2 text-sm text-muted-foreground">Switch to teacher surface to view facilitation notes and answer guidance.</p> : <ul className="mt-2 space-y-1 text-sm text-muted-foreground">{[...notes, ...answers].map((note) => <li key={note}>{note}</li>)}</ul>}</div>;
}

function OnlineMediaPanel({ warnings }: { readonly warnings: readonly string[] }) {
	if (warnings.length === 0) return null;
	return <div className="rounded-md border border-border bg-muted p-3"><p className="text-sm font-medium">Online media warning</p><ul className="mt-2 space-y-1 text-sm text-muted-foreground">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>;
}

function ScopedFeedbackPanel({ scope, feedback, onScopeChange, onFeedbackChange, onSubmit, disabled }: { readonly scope: FeedbackScope; readonly feedback: string; readonly onScopeChange: (scope: FeedbackScope) => void; readonly onFeedbackChange: (feedback: string) => void; readonly onSubmit: () => void; readonly disabled: boolean }) {
	return <div className="rounded-md border border-border bg-card p-3"><p className="text-sm font-medium">Scoped feedback</p><select className="mt-2 h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={scope} onChange={(event) => onScopeChange(feedbackScopeFromValue(event.currentTarget.value))}><option value="deck">Deck</option><option value="slide">Current slide</option><option value="block">First block</option><option value="interaction">First interaction</option></select><textarea className="mt-2 min-h-20 w-full rounded-md border border-input bg-background p-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" value={feedback} onChange={(event) => onFeedbackChange(event.currentTarget.value)} placeholder="What should change at this target?" /><Button type="button" variant="secondary" className="mt-2" disabled={disabled} onClick={onSubmit}>Submit scoped feedback</Button></div>;
}

function artifactPayloads(event: TeachingPackEventPayload): readonly unknown[] {
	const artifacts = event["artifacts"];
	return Array.isArray(artifacts) ? artifacts : [];
}

function parseSlideDeck(value: unknown): SlideDeckData | null {
	if (!isRecord(value)) return null;
	const nestedMetadata = isRecord(value["metadata"]) ? value["metadata"] : null;
	const nestedDeck = nestedMetadata?.["slide_deck_data"] ?? value["slide_deck_data"] ?? value["slide_deck"] ?? value;
	if (!isSlideDeckData(nestedDeck)) return null;
	return nestedDeck;
}

function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isSlideDeckData(value: unknown): value is SlideDeckData {
	if (!isRecord(value) || typeof value["deck_id"] !== "string" || typeof value["title"] !== "string" || !Array.isArray(value["slides"])) return false;
	return value["slides"].every(isSlideDeckSlide);
}

function isSlideDeckSlide(value: unknown): value is SlideDeckSlide {
	return isRecord(value) && typeof value["slide_id"] === "string" && typeof value["title"] === "string" && Array.isArray(value["blocks"]);
}

function feedbackScopeFromValue(value: string): FeedbackScope {
	switch (value) {
		case "deck":
			return "deck";
		case "slide":
			return "slide";
		case "block":
			return "block";
		case "interaction":
			return "interaction";
		default:
			return "slide";
	}
}
