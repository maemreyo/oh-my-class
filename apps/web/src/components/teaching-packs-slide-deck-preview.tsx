"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS, slideDeckPreviewUrl } from "@/hooks/use-teaching-packs";
import type {
	SlideDeckChromeVisibility,
	SlideDeckDisplayPreferences,
	SlideDeckDisplaySurface,
	SlideDeckPrintLayout,
	SlideDeckSlidesPerPage,
	TeachingPackEventPayload,
} from "@/hooks/use-teaching-packs";

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

// ADR-045 (SDTF-05): teacher-only scaffold/stretch guidance, kept separate
// from `teacher_notes` (answer keys). `level` is a plain string, not a fixed
// "scaffold" | "stretch" union, so a future group/level variant is just
// another list item -- see `common.contracts.slide_deck.SlideDeckDifferentiationNote`.
type SlideDeckDifferentiationNote = Readonly<{ level: string; guidance: string }>;

type SlideDeckSlide = Readonly<{
	slide_id: string;
	title: string;
	blocks: readonly SlideDeckBlock[];
	interactions?: readonly SlideDeckInteraction[];
	teacher_notes?: Readonly<{ facilitation_notes?: readonly string[]; answer_key_notes?: readonly string[] }> | null;
	differentiation_guidance?: readonly SlideDeckDifferentiationNote[];
}>;

type SlideDeckData = Readonly<{
	deck_id: string;
	title: string;
	locale?: string;
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

export type SlideDeckTranslationLanguage = "en" | "vi";

export type SlideDeckTranslateRequest = Readonly<{
	snapshot_id: string;
	target_language: SlideDeckTranslationLanguage;
}>;

// SDX-01: EN<->VI only -- the target is always "the other" of the deck's
// current language, never a generic language picker.
function oppositeTranslationLanguage(deck: SlideDeckData | null): SlideDeckTranslationLanguage {
	return deck?.locale?.toLowerCase().startsWith("vi") ? "en" : "vi";
}

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

export function TeachingPacksSlideDeckPreview({ runId, event, onSubmitFeedbackAction, onTranslateDeckAction }: {
	readonly runId: string;
	readonly event: TeachingPackEventPayload;
	readonly onSubmitFeedbackAction?: (feedback: SlideDeckScopedFeedback) => Promise<void> | void;
	readonly onTranslateDeckAction?: (request: SlideDeckTranslateRequest) => Promise<void> | void;
}) {
	const deck = useMemo(() => slideDeckFromEvent(event), [event]);
	const snapshotId = event.snapshot_ids?.[0] ?? "";
	// ADR-043: default view is the clean presentation surface, never the
	// teacher-notes-cluttered one -- matches SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS.
	const [preferences, setPreferences] = useState<SlideDeckDisplayPreferences>(SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS);
	const [slideIndex, setSlideIndex] = useState(0);
	const [feedbackScope, setFeedbackScope] = useState<FeedbackScope>("slide");
	const [feedback, setFeedback] = useState("");
	if (!hasSlideDeckArtifact(event)) return null;

	const slides = deck?.slides ?? [];
	const currentSlide = slides[slideIndex] ?? null;
	const warnings = onlineMediaWarnings(deck);
	const canSubmitFeedback = deck !== null && feedback.trim().length > 0;
	const canTranslate = deck !== null && snapshotId !== "" && onTranslateDeckAction !== undefined;

	return (
		<section className="rounded-lg border border-border bg-background p-4" aria-labelledby="slide-deck-preview-title">
			<div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
				<div>
					<p className="text-xs font-semibold uppercase tracking-wide text-primary">Slide-native review</p>
					<h3 id="slide-deck-preview-title" className="text-lg font-semibold">{deck?.title ?? "Slide deck preview"}</h3>
					<p className="mt-1 text-sm text-muted-foreground">Presentation canvas -- exactly what students see. Teacher, print, and review views live in the panel below.</p>
				</div>
				{canTranslate ? (
					<Button
						type="button"
						variant="secondary"
						onClick={() => onTranslateDeckAction?.({ snapshot_id: snapshotId, target_language: oppositeTranslationLanguage(deck) })}
					>
						Dịch deck này
					</Button>
				) : null}
			</div>

			<PrintSharingPanel preferences={preferences} onChange={setPreferences} />

			<div className="mt-4 grid gap-4 lg:grid-cols-[14rem_minmax(0,1fr)_18rem]">
				<SlideOutline slides={slides} activeIndex={slideIndex} onSelect={setSlideIndex} />
				<div className="space-y-3">
					<SlidePosition slide={currentSlide} index={slideIndex} total={slides.length} />
					<p className="text-xs text-muted-foreground">
						<span className="font-medium text-foreground">{SURFACE_LABELS[preferences.surface]} view</span>
						{" -- "}
						{STUDENT_SAFE_SURFACES.has(preferences.surface) ? "what students will see." : "teacher-only, never shown to students."}
					</p>
					{snapshotId ? (
						<iframe
							key={`${snapshotId}-${preferences.surface}-${preferences.print_layout}-${preferences.slides_per_page}-${preferences.chrome}`}
							title={`Slide deck ${preferences.surface} preview`}
							src={slideDeckPreviewUrl(runId, snapshotId, preferences)}
							className="h-96 w-full rounded-md border border-border bg-card"
							sandbox="allow-same-origin"
						/>
					) : (
						<div className="rounded-md border border-border bg-muted p-6 text-sm text-muted-foreground">Preview snapshot is not ready yet.</div>
					)}
				</div>
				<aside className="space-y-3">
					<TeacherNotesPanel surface={preferences.surface} slide={currentSlide} />
					<DifferentiationGuidancePanel surface={preferences.surface} slide={currentSlide} />
					<OnlineMediaPanel warnings={warnings} />
					{deck ? <ScopedFeedbackPanel scope={feedbackScope} feedback={feedback} onScopeChange={setFeedbackScope} onFeedbackChange={setFeedback} onSubmit={() => onSubmitFeedbackAction?.(createScopedFeedbackPayload(deck, currentSlide, feedbackScope, feedback))} disabled={!canSubmitFeedback} /> : null}
				</aside>
			</div>
		</section>
	);
}

const SLIDE_DECK_SURFACES: readonly SlideDeckDisplaySurface[] = ["presentation", "student", "teacher", "print", "review"];

const SURFACE_LABELS: Readonly<Record<SlideDeckDisplaySurface, string>> = {
	presentation: "Presentation",
	student: "Student",
	teacher: "Teacher",
	print: "Print",
	review: "Review",
};

const SURFACE_DESCRIPTIONS: Readonly<Record<SlideDeckDisplaySurface, string>> = {
	presentation: "Exactly what students see when the deck is presented on screen.",
	student: "Student-safe projection, no facilitation notes or answer keys.",
	teacher: "Includes facilitation notes and answer keys -- never shown to students.",
	print: "Paged or continuous export layout for handouts.",
	review: "Teacher-only, deterministic view used for quality/compliance scanning.",
};

// Surfaces that share the student-safe content boundary (packages/renderer's
// projectSafeDeck) vs. the teacher-only one (projectTeacherDeck) -- see SDH-02.
const STUDENT_SAFE_SURFACES: ReadonlySet<SlideDeckDisplaySurface> = new Set(["presentation", "student"]);

/**
 * Collapsible "Print & sharing" panel (SDH-04): the single place surface,
 * print layout, slides-per-page, and chrome options live, so the main
 * canvas above stays a clean presentation view by default. Every change
 * updates the typed `SlideDeckDisplayPreferences` object, never a raw
 * query string.
 */
function PrintSharingPanel({ preferences, onChange }: {
	readonly preferences: SlideDeckDisplayPreferences;
	readonly onChange: (preferences: SlideDeckDisplayPreferences) => void;
}) {
	return (
		<details className="mt-3 rounded-md border border-border bg-card p-3">
			<summary className="cursor-pointer text-sm font-medium text-foreground">Print &amp; sharing</summary>
			<div className="mt-3 space-y-4 text-sm">
				<fieldset>
					<legend className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Surface</legend>
					<div className="mt-2 flex flex-wrap gap-2" role="group" aria-label="Slide deck preview surface">
						{SLIDE_DECK_SURFACES.map((surface) => (
							<button
								key={surface}
								type="button"
								aria-pressed={surface === preferences.surface}
								className={surface === preferences.surface ? "rounded bg-primary px-3 py-1 text-sm text-primary-foreground" : "rounded border border-border px-3 py-1 text-sm text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"}
								onClick={() => onChange({ ...preferences, surface })}
							>
								{SURFACE_LABELS[surface]}
							</button>
						))}
					</div>
					<p className="mt-2 text-xs text-muted-foreground">
						{STUDENT_SAFE_SURFACES.has(preferences.surface) ? "Student-safe -- " : "Teacher-only -- "}
						{SURFACE_DESCRIPTIONS[preferences.surface]}
					</p>
				</fieldset>

				<div className="grid gap-3 sm:grid-cols-2">
					<label className="block">
						<span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Print layout</span>
						<select
							className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
							value={preferences.print_layout}
							onChange={(event) => onChange({ ...preferences, print_layout: printLayoutFromValue(event.currentTarget.value) })}
						>
							<option value="paged">Paged</option>
							<option value="continuous">Continuous</option>
						</select>
					</label>

					{preferences.print_layout === "paged" ? (
						<label className="block">
							<span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Slides per page</span>
							<select
								className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
								value={String(preferences.slides_per_page)}
								onChange={(event) => onChange({ ...preferences, slides_per_page: slidesPerPageFromValue(event.currentTarget.value) })}
							>
								<option value="1">1</option>
								<option value="2">2</option>
								<option value="4">4</option>
								<option value="6">6</option>
							</select>
						</label>
					) : null}

					<label className="block">
						<span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Chrome</span>
						<select
							className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
							value={preferences.chrome}
							onChange={(event) => onChange({ ...preferences, chrome: chromeFromValue(event.currentTarget.value) })}
						>
							<option value="hidden">Hidden</option>
							<option value="minimal">Minimal</option>
							<option value="branded">Branded</option>
						</select>
					</label>
				</div>
			</div>
		</details>
	);
}

function printLayoutFromValue(value: string): SlideDeckPrintLayout {
	return value === "continuous" ? "continuous" : "paged";
}

function slidesPerPageFromValue(value: string): SlideDeckSlidesPerPage {
	const parsed = Number(value);
	return parsed === 2 || parsed === 4 || parsed === 6 ? parsed : 1;
}

function chromeFromValue(value: string): SlideDeckChromeVisibility {
	return value === "minimal" || value === "branded" ? value : "hidden";
}

function SlideOutline({ slides, activeIndex, onSelect }: { readonly slides: readonly SlideDeckSlide[]; readonly activeIndex: number; readonly onSelect: (index: number) => void }) {
	if (slides.length === 0) return <div className="rounded-md border border-border bg-muted p-3 text-sm text-muted-foreground">Slide outline will appear when deck metadata is available.</div>;
	return <nav aria-label="Slide outline" className="space-y-2">{slides.map((slide, index) => <button key={slide.slide_id} type="button" className={index === activeIndex ? "w-full rounded-md border border-primary bg-muted p-3 text-left text-sm" : "w-full rounded-md border border-border bg-card p-3 text-left text-sm hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"} onClick={() => onSelect(index)}><span className="block text-xs font-medium text-muted-foreground">Slide {index + 1}</span><span className="mt-1 block font-medium">{slide.title}</span></button>)}</nav>;
}

function SlidePosition({ slide, index, total }: { readonly slide: SlideDeckSlide | null; readonly index: number; readonly total: number }) {
	return <div className="flex items-center justify-between rounded-md border border-border bg-card px-3 py-2 text-sm"><span className="font-medium">{slide?.title ?? "Deck preview"}</span><span className="text-muted-foreground">{total > 0 ? `${index + 1} / ${total}` : "No slide metadata"}</span></div>;
}

function TeacherNotesPanel({ surface, slide }: { readonly surface: SlideDeckDisplaySurface; readonly slide: SlideDeckSlide | null }) {
	// This panel is a sibling of the slide canvas, never inside it -- teacher
	// notes/answer keys are only ever mixed into this separate DOM subtree,
	// and only when the teacher explicitly selects a teacher-only surface.
	const showTeacherContent = surface === "teacher" || surface === "review";
	const notes = showTeacherContent ? slide?.teacher_notes?.facilitation_notes ?? [] : [];
	const answers = showTeacherContent ? slide?.teacher_notes?.answer_key_notes ?? [] : [];
	return <div className="rounded-md border border-border bg-card p-3"><p className="text-sm font-medium">Teacher notes</p>{!showTeacherContent ? <p className="mt-2 text-sm text-muted-foreground">Switch to the teacher or review surface to view facilitation notes and answer guidance.</p> : <ul className="mt-2 space-y-1 text-sm text-muted-foreground">{[...notes, ...answers].map((note) => <li key={note}>{note}</li>)}</ul>}</div>;
}

// ADR-045 (SDTF-05): the teacher-only differentiation planning panel -- a
// sibling of `TeacherNotesPanel`, never merged into it, so "how to adapt for
// scaffold/stretch" stays visually and structurally distinct from "what the
// answer is". Same student-safe surface gate as `TeacherNotesPanel`.
function DifferentiationGuidancePanel({ surface, slide }: { readonly surface: SlideDeckDisplaySurface; readonly slide: SlideDeckSlide | null }) {
	const showTeacherContent = surface === "teacher" || surface === "review";
	const notes = showTeacherContent ? slide?.differentiation_guidance ?? [] : [];
	return (
		<div className="rounded-md border border-border bg-card p-3">
			<p className="text-sm font-medium">Differentiation guidance</p>
			{!showTeacherContent ? (
				<p className="mt-2 text-sm text-muted-foreground">Switch to the teacher or review surface to view scaffold/stretch guidance.</p>
			) : notes.length === 0 ? (
				<p className="mt-2 text-sm text-muted-foreground">No differentiation guidance for this slide yet.</p>
			) : (
				<ul className="mt-2 space-y-1 text-sm text-muted-foreground">
					{notes.map((note, index) => (
						<li key={`${note.level}-${index}`}><span className="font-medium capitalize text-foreground">{note.level}:</span> {note.guidance}</li>
					))}
				</ul>
			)}
		</div>
	);
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
