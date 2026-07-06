"use client";

import type { TeachingPackEventPayload } from "@/hooks/use-teaching-packs";
import { humanize, strategyPlanViewFromEvent, uniqueStrings } from "@/components/teaching-packs-strategy-panel-model";
import type { ArtifactProjectionView, StrategyPlanView, StrategySlotView, StrategyVariantView } from "@/components/teaching-packs-strategy-panel-model";

export type StrategyFeedbackType =
	| "prefer_component_family"
	| "reject_component_family"
	| "prefer_learning_move"
	| "reject_learning_move"
	| "request_more_practice"
	| "request_lower_teacher_load";

export interface StrategyFeedbackDraft {
	readonly event_type: StrategyFeedbackType;
	readonly value: string;
	readonly rationale?: string;
}

interface StrategyPanelProps {
	readonly event: TeachingPackEventPayload;
	readonly onFeedback?: (draft: StrategyFeedbackDraft) => void;
}

export function TeachingPackStrategyPanel({ event, onFeedback }: StrategyPanelProps) {
	const plan = strategyPlanViewFromEvent(event);
	if (!plan) return null;

	const componentTypes = uniqueStrings(plan.recommended.slots.map((slot) => slot.componentType));
	const learningMoves = uniqueStrings(plan.recommended.slots.map((slot) => slot.learningMoveId));
	const variants = plan.variants.filter((variant) => !variant.fallbackNote).slice(0, 2);
	const fallbackNotes = uniqueStrings([plan.recommended, ...plan.variants].map((variant) => variant.fallbackNote));
	const primaryComponent = componentTypes[0] ?? plan.recommended.strategyFamilyId;
	const primaryMove = learningMoves[0] ?? plan.recommended.strategyFamilyId;

	return (
		<section aria-labelledby="strategy-panel-title" className="rounded-lg border border-border bg-card p-4">
			<div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div className="space-y-1">
					<p className="text-xs font-semibold uppercase tracking-wide text-primary">Teaching strategy</p>
					<h3 id="strategy-panel-title" className="text-lg font-semibold">{plan.recommended.displayLabel}</h3>
					<p className="max-w-3xl text-sm text-muted-foreground">{plan.rationale}</p>
				</div>
				<span className="rounded-full border border-border bg-muted px-3 py-1 text-xs font-semibold text-foreground">
					{plan.recommended.fitLabel}
				</span>
			</div>

			<div className="mt-4 grid gap-3 sm:grid-cols-2">
				<StrategyChipGroup title="Learning moves" values={learningMoves} />
				<StrategyChipGroup title="Component types" values={componentTypes} />
			</div>

			{fallbackNotes.length > 0 ? <FallbackNotes notes={fallbackNotes} /> : null}
			<StrategyDetails plan={plan} />
			<StrategyFeedbackControls
				variants={variants}
				primaryComponent={primaryComponent}
				primaryMove={primaryMove}
				onFeedback={onFeedback}
			/>
		</section>
	);
}

function StrategyChipGroup({ title, values }: { readonly title: string; readonly values: readonly string[] }) {
	return (
		<div className="rounded-md bg-background p-3">
			<p className="text-sm font-medium">{title}</p>
			<div className="mt-2 flex flex-wrap gap-2">
				{values.length > 0 ? (
					values.map((value) => <span key={value} className="rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground">{humanize(value)}</span>)
				) : (
					<span className="text-sm text-muted-foreground">Not specified</span>
				)}
			</div>
		</div>
	);
}

function FallbackNotes({ notes }: { readonly notes: readonly string[] }) {
	return (
		<div className="mt-4 rounded-md border border-border bg-muted p-3 text-sm">
			<p className="font-medium">Fallback note</p>
			<ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
				{notes.map((note) => <li key={note}>{note}</li>)}
			</ul>
		</div>
	);
}

function StrategyDetails({ plan }: { readonly plan: StrategyPlanView }) {
	return (
		<details className="mt-4 rounded-md border border-border bg-background p-3">
			<summary className="cursor-pointer text-sm font-medium text-foreground">View strategy details</summary>
			<div className="mt-3 space-y-4 text-sm">
				<OrderedMoves slots={plan.recommended.slots} />
				<ArtifactProjection artifacts={plan.recommended.artifacts} />
				<WarningList title="Tradeoffs" warnings={plan.tradeoffs} />
				<WarningList title="Export warnings" warnings={plan.recommended.exportWarnings} />
				<div className="rounded-md bg-muted p-3">
					<p className="font-medium">Student-facing and teacher-only split</p>
					<p className="mt-1 text-muted-foreground">
						Student pages receive selected practice components. Teacher-only output keeps rationale, answer keys, and strategy notes out of student-facing artifacts.
					</p>
				</div>
			</div>
		</details>
	);
}

function StrategyFeedbackControls({ variants, primaryComponent, primaryMove, onFeedback }: {
	readonly variants: readonly StrategyVariantView[];
	readonly primaryComponent: string;
	readonly primaryMove: string;
	readonly onFeedback?: (draft: StrategyFeedbackDraft) => void;
}) {
	return (
		<div className="mt-4 grid gap-3 lg:grid-cols-2">
			<div className="rounded-md bg-muted p-3">
				<p className="text-sm font-medium">Optional variants</p>
				{variants.length > 0 ? (
					<div className="mt-2 space-y-2">
						{variants.map((variant) => (
							<button key={variant.variantId} type="button" className="w-full rounded-md border border-border bg-background px-3 py-2 text-left text-sm hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring" onClick={() => onFeedback?.({ event_type: "prefer_component_family", value: variant.strategyFamilyId, rationale: `Switch to ${variant.displayLabel}` })}>
								<span className="font-medium">{variant.displayLabel}</span>
								<span className="block text-muted-foreground">{variant.fitLabel}</span>
							</button>
						))}
					</div>
				) : (
					<p className="mt-2 text-sm text-muted-foreground">No safer alternate strategy is available for this blueprint.</p>
				)}
			</div>

			<div className="rounded-md bg-muted p-3">
				<p className="text-sm font-medium">Bounded strategy feedback</p>
				<div className="mt-2 grid gap-2 sm:grid-cols-2">
					<FeedbackButton label="More practice" draft={{ event_type: "request_more_practice", value: primaryComponent }} onFeedback={onFeedback} />
					<FeedbackButton label="Lower teacher load" draft={{ event_type: "request_lower_teacher_load", value: primaryMove }} onFeedback={onFeedback} />
					<FeedbackButton label="Use more of this" draft={{ event_type: "prefer_component_family", value: primaryComponent }} onFeedback={onFeedback} />
					<FeedbackButton label="Use less of this" draft={{ event_type: "reject_component_family", value: primaryComponent }} onFeedback={onFeedback} />
				</div>
				<p className="mt-2 text-xs text-muted-foreground">Exact component placement stays engine-owned in this version.</p>
			</div>
		</div>
	);
}

function FeedbackButton({ label, draft, onFeedback }: { readonly label: string; readonly draft: StrategyFeedbackDraft; readonly onFeedback?: (draft: StrategyFeedbackDraft) => void }) {
	return <button type="button" className="rounded-md border border-border bg-background px-3 py-2 text-sm hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring" onClick={() => onFeedback?.(draft)}>{label}</button>;
}

function OrderedMoves({ slots }: { readonly slots: readonly StrategySlotView[] }) {
	return <div className="rounded-md bg-muted p-3"><p className="font-medium">Ordered moves</p><ol className="mt-2 list-decimal space-y-1 pl-5 text-muted-foreground">{slots.map((slot) => <li key={slot.slotId}>{humanize(slot.phase)}: {humanize(slot.learningMoveId)} with {humanize(slot.componentType)} for {slot.targetArtifacts.join(", ")}</li>)}</ol></div>;
}

function ArtifactProjection({ artifacts }: { readonly artifacts: readonly ArtifactProjectionView[] }) {
	return <div className="rounded-md bg-muted p-3"><p className="font-medium">Artifact projections</p><ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">{artifacts.map((artifact) => <li key={artifact.artifactType}>{humanize(artifact.artifactType)} uses {artifact.orderedSlotIds.length} strategy slot(s){artifact.notes.length > 0 ? `: ${artifact.notes.join("; ")}` : "."}</li>)}</ul></div>;
}

function WarningList({ title, warnings }: { readonly title: string; readonly warnings: readonly string[] }) {
	if (warnings.length === 0) return null;
	return <div className="rounded-md bg-muted p-3"><p className="font-medium">{title}</p><ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>;
}
