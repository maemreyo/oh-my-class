"use client";

import { useState } from "react";
import type { SlideDeckData, SlideDeckSlide } from "@oh-my-class/schemas";
import { Button } from "@/components/ui/button";
import { SlideCanvas } from "./slide-canvas";

/**
 * SDE-03: purpose-built editing canvas over `SlideDeckData`. UI-only — edits
 * live in local state; there is no save/edit-API yet (that's SDE-04). The
 * "Save changes" action below is a marked stub, not a working save path.
 */
export function SlideDeckEditor({ initialDeck }: { readonly initialDeck: SlideDeckData }) {
	const [deck, setDeck] = useState(initialDeck);
	const [slideIndex, setSlideIndex] = useState(0);
	const currentSlide = deck.slides[slideIndex] ?? null;

	function updateSlide(updated: SlideDeckSlide) {
		setDeck((previous) => ({
			...previous,
			slides: previous.slides.map((slide) => (slide.slide_id === updated.slide_id ? updated : slide)),
		}));
	}

	return (
		<div className="flex h-full min-h-0 flex-1">
			<nav aria-label="Slide outline" className="w-56 shrink-0 space-y-2 overflow-y-auto border-r border-border bg-card p-3">
				{deck.slides.map((slide, index) => (
					<button
						key={slide.slide_id}
						type="button"
						onClick={() => setSlideIndex(index)}
						className={
							index === slideIndex
								? "w-full rounded-md border border-primary bg-muted p-2 text-left text-sm"
								: "w-full rounded-md border border-border bg-background p-2 text-left text-sm hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
						}
					>
						<span className="block text-xs text-muted-foreground">Slide {index + 1}</span>
						<span className="block font-medium">{slide.title}</span>
					</button>
				))}
			</nav>
			<div className="min-w-0 flex-1 overflow-y-auto p-6">
				<div className="mx-auto max-w-3xl space-y-4">
					<div className="flex items-center justify-between gap-4">
						<h1 className="min-w-0 truncate text-xl font-semibold">{deck.title}</h1>
						<Button
							type="button"
							variant="outline"
							size="sm"
							disabled
							title="Saving edits ships in SDE-04 (edit-API/versioning)"
						>
							Save changes (coming soon)
						</Button>
					</div>
					{currentSlide ? (
						<SlideCanvas slide={currentSlide} onSlideChange={updateSlide} />
					) : (
						<p className="text-sm text-muted-foreground">No slides in this deck.</p>
					)}
				</div>
			</div>
		</div>
	);
}
