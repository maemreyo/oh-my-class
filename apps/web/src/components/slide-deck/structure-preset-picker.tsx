"use client";

// SDX-03: fixed, curated list of system deck-structure presets, selectable
// at deck-creation time. Mirrors `SLIDE_DECK_STRUCTURE_PRESETS` in
// `packages/agents/slide_deck_engine/structure_presets.py` -- ids must match
// exactly since `id` (or "" for none) is the `structure_preset` value sent
// to the engine. No "save current deck as a preset" affordance exists here
// or anywhere else in this slice.

export type SlideDeckStructurePresetId = "5e_model" | "direct_instruction" | "flipped_intro";

export interface SlideDeckStructurePreset {
	readonly id: SlideDeckStructurePresetId;
	readonly label: string;
	readonly description: string;
}

export const SLIDE_DECK_STRUCTURE_PRESETS: readonly SlideDeckStructurePreset[] = [
	{ id: "5e_model", label: "5E model", description: "Engage-Explore-Explain-Elaborate-Evaluate. Students explore first; the pattern is named after." },
	{ id: "direct_instruction", label: "Direct instruction", description: "Teacher models the skill, then students practice the same pattern right away." },
	{ id: "flipped_intro", label: "Flipped intro", description: "Students arrive with prior exposure; class time recaps and builds on it in a shorter slot." },
];

export function StructurePresetPicker({
	selectedPresetId,
	onSelectAction,
}: {
	readonly selectedPresetId: SlideDeckStructurePresetId | null;
	readonly onSelectAction?: (presetId: SlideDeckStructurePresetId | null) => void;
}) {
	return (
		<section aria-label="Deck structure preset picker" className="space-y-3">
			<div>
				<h3 className="text-lg font-semibold">Structure preset</h3>
				<p className="mt-1 text-sm text-muted-foreground">
					Optional starting point for the deck&apos;s slide structure and pacing. Leave unselected for the default flow.
				</p>
			</div>
			<div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
				<button
					type="button"
					aria-pressed={selectedPresetId === null}
					onClick={() => onSelectAction?.(null)}
					className="rounded-lg border border-border bg-card p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[selected=true]:border-primary data-[selected=true]:bg-primary/10"
					data-selected={selectedPresetId === null}
				>
					<span className="block text-sm font-semibold">Default (no preset)</span>
					<span className="mt-1 block text-sm text-foreground/80">Standard six-slide flow with no structural framing applied.</span>
				</button>
				{SLIDE_DECK_STRUCTURE_PRESETS.map((preset) => {
					const selected = selectedPresetId === preset.id;
					return (
						<button
							key={preset.id}
							type="button"
							aria-pressed={selected}
							onClick={() => onSelectAction?.(preset.id)}
							className="rounded-lg border border-border bg-card p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[selected=true]:border-primary data-[selected=true]:bg-primary/10"
							data-selected={selected}
						>
							<span className="block text-sm font-semibold">{preset.label}</span>
							<span className="mt-1 block text-sm text-foreground/80">{preset.description}</span>
						</button>
					);
				})}
			</div>
		</section>
	);
}
