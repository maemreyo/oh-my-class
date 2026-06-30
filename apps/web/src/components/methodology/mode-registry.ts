import { METHODOLOGY_REGISTRY } from "../../../../../common/schemas/src/generated/methodology_registry";
import type { MethodologyMetadata } from "../../../../../common/schemas/src/generated/lesson_plan";

import { TEMPLATE_REFERENCE_MODES, type TemplateReferenceTag } from "./template-reference-modes";

type GeneratedMethodologyTag = NonNullable<MethodologyMetadata["tags"]>[number];

export type MethodologyTag =
	| "standard"
	| GeneratedMethodologyTag
	| TemplateReferenceTag;

export interface MethodologyMode {
	readonly tag: MethodologyTag;
	readonly label: string;
	readonly labelVi?: string;
	readonly description: string;
	readonly requiredComponents: readonly string[];
	readonly supportedArtifacts?: readonly string[];
	readonly exportFormats?: readonly string[];
	readonly conflicts?: readonly string[];
	readonly compatibleWith?: readonly string[];
}

export const METHODOLOGY_MODES: readonly MethodologyMode[] = [
	{ tag: "standard", label: "Standard", description: "Balanced teaching pack without a specialized methodology overlay.", requiredComponents: [] },
	...METHODOLOGY_REGISTRY.map((entry) => ({
		tag: entry.tag,
		label: entry.labelEn,
		labelVi: entry.labelVi,
		description: entry.description,
		requiredComponents: [...entry.requiredComponents],
			supportedArtifacts: [...entry.supportedArtifacts],
			exportFormats: [...entry.exportFormats],
			conflicts: [...entry.conflicts],
			compatibleWith: [...entry.compatibleWith],
		})),
	...TEMPLATE_REFERENCE_MODES.map((mode) => ({
		tag: mode.tag,
		label: mode.label,
		description: `${mode.description} Coming soon as a tokenized reference mode.`,
		requiredComponents: [...mode.rendererSurfaces],
	})),
];

export function modeByTag(tag: string): MethodologyMode | null {
	return METHODOLOGY_MODES.find((mode) => mode.tag === tag) ?? null;
}

export type MethodologyPairStatus = "compatible" | "conflict" | "neutral";

export function classifyMethodologyPair(left: string, right: string): MethodologyPairStatus {
	const leftMode = modeByTag(left);
	const rightMode = modeByTag(right);
	if (!leftMode || !rightMode || left === "standard" || right === "standard") return "neutral";
	if (left === right || leftMode.compatibleWith?.includes(right) || rightMode.compatibleWith?.includes(left)) return "compatible";
	if (leftMode.conflicts?.includes(right) || rightMode.conflicts?.includes(left)) return "conflict";
	return "neutral";
}

export function conflictRationale(left: string, right: string): string | null {
	if (classifyMethodologyPair(left, right) !== "conflict") return null;
	return `${modeByTag(left)?.label ?? left} conflicts with ${modeByTag(right)?.label ?? right}: timed public pressure does not fit private rehearsal flows.`;
}

export function combinedPreviewMetadata(tags: readonly string[]): string | null {
	const active = tags.filter((tag) => tag !== "standard");
	if (active.length < 2) return null;
	return `Combined preview: ${active.map((tag) => modeByTag(tag)?.label ?? tag).join(" + ")}`;
}
