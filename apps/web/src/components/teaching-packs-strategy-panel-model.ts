import type { TeachingPackEventPayload } from "@/hooks/use-teaching-packs";

export interface StrategyPlanView {
	readonly recommended: StrategyVariantView;
	readonly rationale: string;
	readonly variants: readonly StrategyVariantView[];
	readonly tradeoffs: readonly string[];
}

export interface StrategyVariantView {
	readonly variantId: string;
	readonly strategyFamilyId: string;
	readonly displayLabel: string;
	readonly slots: readonly StrategySlotView[];
	readonly artifacts: readonly ArtifactProjectionView[];
	readonly exportWarnings: readonly string[];
	readonly fallbackNote: string;
	readonly fitLabel: string;
}

export interface StrategySlotView {
	readonly slotId: string;
	readonly phase: string;
	readonly learningMoveId: string;
	readonly componentType: string;
	readonly targetArtifacts: readonly string[];
}

export interface ArtifactProjectionView {
	readonly artifactType: string;
	readonly orderedSlotIds: readonly string[];
	readonly notes: readonly string[];
}

export function strategyPlanViewFromEvent(event: TeachingPackEventPayload): StrategyPlanView | null {
	const plan = recordAt(event, "component_strategy_plan") ?? recordAt(recordAt(event, "component_strategy_result"), "plan");
	if (!plan) return null;
	const recommended = variantViewFromRecord(recordAt(plan, "recommended"));
	if (!recommended) return null;
	return {
		recommended,
		rationale: stringAt(plan, "rationale_text", "Strategy is selected from the lesson blueprint and research signals."),
		variants: arrayAt(plan, "variants").map(variantFromUnknown).filter((variant) => variant !== null),
		tradeoffs: arrayAt(plan, "rationale_facts").map(readableUnknown),
	};
}

export function uniqueStrings(values: readonly string[]): readonly string[] {
	return Array.from(new Set(values.filter((value) => value.length > 0)));
}

export function humanize(value: string): string {
	return value.replaceAll("_", " ");
}

function variantFromUnknown(value: unknown): StrategyVariantView | null {
	return variantViewFromRecord(recordFromUnknown(value));
}

function variantViewFromRecord(record: Readonly<Record<string, unknown>> | null): StrategyVariantView | null {
	if (!record) return null;
	const slots = arrayAt(record, "learning_sequence").map(slotFromUnknown).filter((slot) => slot !== null);
	const artifacts = arrayAt(record, "artifact_strategies").map(artifactFromUnknown).filter((artifact) => artifact !== null);
	if (slots.length === 0 || artifacts.length === 0) return null;
	const fallback = recordAt(record, "fallback_metadata");
	return {
		variantId: stringAt(record, "variant_id", stringAt(record, "strategy_family_id", "variant")),
		strategyFamilyId: stringAt(record, "strategy_family_id", "strategy_family"),
		displayLabel: stringAt(record, "display_label", humanize(stringAt(record, "strategy_family_id", "Recommended strategy"))),
		slots,
		artifacts,
		exportWarnings: arrayAt(record, "export_projection_status").map(exportWarningFromUnknown).filter((warning) => warning.length > 0),
		fallbackNote: fallback ? stringAt(fallback, "teacher_visible_note", "") : "",
		fitLabel: fitLabel(recordAt(record, "quality_score"), fallback),
	};
}

function slotFromUnknown(value: unknown): StrategySlotView | null {
	const record = recordFromUnknown(value);
	if (!record) return null;
	return {
		slotId: stringAt(record, "slot_id", "slot"),
		phase: stringAt(record, "phase", "phase"),
		learningMoveId: stringAt(record, "learning_move_id", "learning_move"),
		componentType: stringAt(record, "component_type", "component"),
		targetArtifacts: arrayAt(record, "target_artifacts").map(readableUnknown),
	};
}

function artifactFromUnknown(value: unknown): ArtifactProjectionView | null {
	const record = recordFromUnknown(value);
	if (!record) return null;
	return {
		artifactType: stringAt(record, "artifact_type", "artifact"),
		orderedSlotIds: arrayAt(record, "ordered_slot_ids").map(readableUnknown),
		notes: arrayAt(record, "notes_for_creator").map(readableUnknown),
	};
}

function exportWarningFromUnknown(value: unknown): string {
	const record = recordFromUnknown(value);
	if (!record) return "";
	const reason = stringAt(record, "reason", "");
	const fallback = stringAt(record, "fallback_component_type", "");
	if (reason && fallback) return `${humanize(stringAt(record, "export_format", "export"))}: ${reason}; fallback ${humanize(fallback)}`;
	return reason;
}

function fitLabel(score: Readonly<Record<string, unknown>> | null, fallback: Readonly<Record<string, unknown>> | null): string {
	if (fallback) return "Fallback used";
	const overall = numberAt(score, "overall");
	if (overall === null) return "Ready for review";
	if (overall >= 0.85) return "Strong fit";
	if (overall >= 0.7) return "Good fit with tradeoff";
	return "Needs teacher choice";
}

function recordAt(source: Readonly<Record<string, unknown>> | null, key: string): Readonly<Record<string, unknown>> | null {
	if (!source) return null;
	return recordFromUnknown(source[key]);
}

function recordFromUnknown(value: unknown): Readonly<Record<string, unknown>> | null {
	if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
	return Object.fromEntries(Object.entries(value));
}

function arrayAt(source: Readonly<Record<string, unknown>>, key: string): readonly unknown[] {
	const value = source[key];
	return Array.isArray(value) ? value : [];
}

function stringAt(source: Readonly<Record<string, unknown>> | null, key: string, fallback: string): string {
	if (!source) return fallback;
	const value = source[key];
	return typeof value === "string" && value.length > 0 ? value : fallback;
}

function numberAt(source: Readonly<Record<string, unknown>> | null, key: string): number | null {
	if (!source) return null;
	const value = source[key];
	return typeof value === "number" ? value : null;
}

function readableUnknown(value: unknown): string {
	if (typeof value === "string") return value;
	if (typeof value === "number" || typeof value === "boolean") return String(value);
	if (value === null || value === undefined) return "";
	return Object.values(recordFromUnknown(value) ?? {}).map(readableUnknown).filter((item) => item.length > 0).join(" · ");
}
