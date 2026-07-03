import type { TeachingPackEventPayload, TeachingPackGateName } from "@/hooks/use-teaching-packs";
import type { EditableArtifactTarget } from "@/components/teaching-packs-scoped-rejection";


export function editableArtifactsFor(
	event: TeachingPackEventPayload,
	fallback: readonly { readonly artifact_id: string; readonly artifact_type: string }[],
): readonly EditableArtifactTarget[] {
	const fromContentArtifacts = editableArtifactsFromUnknownList(event.content_artifacts);
	if (fromContentArtifacts.length > 0) return fromContentArtifacts;
	return fallback.map((artifact) => ({ id: artifact.artifact_id, type: artifact.artifact_type }));
}


export function responseFor(gateName: TeachingPackGateName, feedback: string): Readonly<Record<string, unknown>> {
	const trimmed = feedback.trim();
	if (!trimmed) return {};
	if (gateName === "clarification_required") return { answer: trimmed };
	return { feedback: trimmed };
}


export function gateNameFor(event: TeachingPackEventPayload): TeachingPackGateName | null {
	const candidate = event.gate_name ?? event.gate;
	if (isGateName(candidate)) return candidate;
	return null;
}


export function labelFor(gateName: TeachingPackGateName): string {
	switch (gateName) {
		case "clarification_required":
			return "Clarification required";
		case "contract_confirmation":
			return "Confirm the teaching contract";
		case "search_plan_confirmation":
			return "Confirm the research plan";
		case "blueprint_approval":
			return "Review the blueprint";
		case "content_approval":
			return "Review rendered content";
		case "unit_approval":
			return "Review the unit sequence";
		default:
			return assertNever(gateName);
	}
}


function editableArtifactsFromUnknownList(value: unknown): readonly EditableArtifactTarget[] {
	if (!Array.isArray(value)) return [];
	return value.map(editableArtifactFromUnknown).filter((artifact) => artifact !== null);
}


function editableArtifactFromUnknown(value: unknown): EditableArtifactTarget | null {
	if (!isRecord(value)) return null;
	const id = stringField(value, "artifact_id") ?? stringField(value, "id");
	const type = stringField(value, "artifact_type") ?? stringField(value, "type");
	if (!id || !type) return null;
	return {
		id,
		type,
		sections: sectionTargetsFromUnknown(value.sections),
	};
}


function sectionTargetsFromUnknown(value: unknown): readonly { readonly section_id: string; readonly title: string; readonly content: string }[] {
	if (!Array.isArray(value)) return [];
	return value.map(sectionTargetFromUnknown).filter((section) => section !== null);
}


function sectionTargetFromUnknown(value: unknown): { readonly section_id: string; readonly title: string; readonly content: string } | null {
	if (!isRecord(value)) return null;
	const sectionId = stringField(value, "section_id") ?? stringField(value, "id");
	const content = stringField(value, "content") ?? "";
	if (!sectionId) return null;
	const title = stringField(value, "title") ?? sectionId;
	return { section_id: sectionId, title, content };
}


function stringField(record: Readonly<Record<string, unknown>>, key: string): string | null {
	const value = record[key];
	if (typeof value === "string" && value.length > 0) return value;
	return null;
}


function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}


function isGateName(value: unknown): value is TeachingPackGateName {
	switch (value) {
		case "clarification_required":
		case "contract_confirmation":
		case "search_plan_confirmation":
		case "blueprint_approval":
		case "content_approval":
		case "unit_approval":
			return true;
		default:
			return false;
	}
}


function assertNever(value: never): never {
	throw new Error(`Unhandled gate: ${String(value)}`);
}
