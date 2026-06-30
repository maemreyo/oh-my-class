"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export type TeachingApproach = "auto" | "standard" | "inverse_thinking";

export type CreativeFrameId =
	| "auto"
	| "detective_case"
	| "courtroom_trial"
	| "mythbusters_lab"
	| "survival_guide"
	| "disaster_report"
	| "custom";

export interface InverseThinkingCaseDraft {
	id: string;
	title: string;
	foil: string;
	disaster: string;
	key_clues: string[];
	safe_zone: string;
	filing_note: string;
	student_task: string;
}

export interface InverseThinkingEditorState {
	approach: TeachingApproach;
	creativeFrame: CreativeFrameId;
	intensity: "light" | "balanced" | "intensive";
	studentOutput: "print" | "interactive";
	caseDraft: InverseThinkingCaseDraft;
	qualityWarnings: string[];
	inspectorOpen: boolean;
}

export interface RegenerationPayload {
	scope: "field" | "case";
	case_id: string;
	field?: keyof InverseThinkingCaseDraft;
}

export type WrongReasonDraft = Readonly<Record<string, string>>;

export const CREATIVE_FRAME_OPTIONS: readonly { id: CreativeFrameId; label: string }[] = [
	{ id: "auto", label: "Auto" },
	{ id: "detective_case", label: "Detective Case" },
	{ id: "courtroom_trial", label: "Courtroom Trial" },
	{ id: "mythbusters_lab", label: "Mythbusters Lab" },
	{ id: "survival_guide", label: "Survival Guide" },
	{ id: "disaster_report", label: "Disaster Report" },
	{ id: "custom", label: "Custom" },
];

export const DEFAULT_INVERSE_THINKING_CASE: InverseThinkingCaseDraft = {
	id: "case-1",
	title: "Case file",
	foil: "Common misconception",
	disaster: "A student makes a visible mistake.",
	key_clues: ["observable clue"],
	safe_zone: "Use the safe boundary rule.",
	filing_note: "Connect the clue to the safe rule.",
	student_task: "Find the unsafe part and repair it.",
};

export function updateInverseThinkingCase(
	draft: InverseThinkingCaseDraft,
	field: keyof InverseThinkingCaseDraft,
	value: string,
): InverseThinkingCaseDraft {
	if (field === "key_clues") {
		return {
			...draft,
			key_clues: value.split("\n").map((item) => item.trim()).filter(Boolean),
		};
	}
	return { ...draft, [field]: value };
}

export function createRegenerationPayload(
	draft: InverseThinkingCaseDraft,
	scope: "field" | "case",
	field?: keyof InverseThinkingCaseDraft,
): RegenerationPayload {
	return { scope, case_id: draft.id, field };
}

export function validateInverseThinkingDraft(draft: InverseThinkingCaseDraft): string[] {
	const errors: string[] = [];
	if (draft.foil.trim().length === 0) errors.push("cases.0.foil");
	if (draft.disaster.trim().length === 0) errors.push("cases.0.disaster");
	if (draft.key_clues.length === 0) errors.push("cases.0.key_clues");
	if (draft.safe_zone.trim().length === 0) errors.push("cases.0.safe_zone");
	if (draft.filing_note.trim().length === 0) errors.push("cases.0.filing_note");
	if (draft.student_task.trim().length === 0) errors.push("cases.0.student_task");
	return errors;
}

export function updateWrongReasonDraft(
	draft: WrongReasonDraft,
	optionKey: string,
	value: string,
): WrongReasonDraft {
	return { ...draft, [optionKey]: value };
}

export function validateWrongReasons(
	options: Readonly<Record<string, string>>,
	answer: string,
	wrongReasons: WrongReasonDraft,
): string[] {
	return Object.keys(options)
		.filter((optionKey) => optionKey !== answer)
		.filter((optionKey) => !wrongReasons[optionKey]?.trim())
		.map((optionKey) => `wrong_reasons.${optionKey}`);
}

interface InverseThinkingEditorProps {
	initialState?: Partial<InverseThinkingEditorState>;
	renderedHtml?: string;
	onRegenerate?: (payload: RegenerationPayload) => void;
}

export function InverseThinkingEditor({
	initialState,
	renderedHtml = "",
	onRegenerate,
}: InverseThinkingEditorProps) {
	const [state, setState] = React.useState<InverseThinkingEditorState>({
		approach: initialState?.approach ?? "auto",
		creativeFrame: initialState?.creativeFrame ?? "auto",
		intensity: initialState?.intensity ?? "balanced",
		studentOutput: initialState?.studentOutput ?? "print",
		caseDraft: initialState?.caseDraft ?? DEFAULT_INVERSE_THINKING_CASE,
		qualityWarnings: initialState?.qualityWarnings ?? [],
		inspectorOpen: initialState?.inspectorOpen ?? false,
	});
	const errors = validateInverseThinkingDraft(state.caseDraft);
	const inverseSelected = state.approach === "inverse_thinking";

	function setCaseField(field: keyof InverseThinkingCaseDraft, value: string): void {
		setState((current) => ({
			...current,
			caseDraft: updateInverseThinkingCase(current.caseDraft, field, value),
		}));
	}

	function regenerate(scope: "field" | "case", field?: keyof InverseThinkingCaseDraft): void {
		onRegenerate?.(createRegenerationPayload(state.caseDraft, scope, field));
	}

	return (
		<section className="space-y-6" aria-label="Inverse Thinking structured editor">
			<label className="block space-y-2">
				<span className="text-sm font-medium">Teaching approach</span>
				<select
					className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
					value={state.approach}
					onChange={(event) => setState({ ...state, approach: event.currentTarget.value as TeachingApproach })}
				>
					<option value="auto">Auto</option>
					<option value="standard">Standard</option>
					<option value="inverse_thinking">Inverse Thinking</option>
				</select>
			</label>

			{inverseSelected ? (
				<div className="space-y-5 rounded-lg border border-border bg-card p-4">
					<div className="grid gap-4 md:grid-cols-3">
						<label className="space-y-2">
							<span className="text-sm font-medium">Creative direction</span>
							<select
								className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
								value={state.creativeFrame}
								onChange={(event) => setState({ ...state, creativeFrame: event.currentTarget.value as CreativeFrameId })}
							>
								{CREATIVE_FRAME_OPTIONS.map((frame) => <option key={frame.id} value={frame.id}>{frame.label}</option>)}
							</select>
						</label>
						<label className="space-y-2">
							<span className="text-sm font-medium">Intensity</span>
							<select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={state.intensity} onChange={(event) => setState({ ...state, intensity: event.currentTarget.value as InverseThinkingEditorState["intensity"] })}>
								<option value="light">Light</option>
								<option value="balanced">Balanced</option>
								<option value="intensive">Intensive</option>
							</select>
						</label>
						<label className="space-y-2">
							<span className="text-sm font-medium">Student output</span>
							<select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={state.studentOutput} onChange={(event) => setState({ ...state, studentOutput: event.currentTarget.value as InverseThinkingEditorState["studentOutput"] })}>
								<option value="print">Print-ready</option>
								<option value="interactive">Interactive preview</option>
							</select>
						</label>
					</div>

					<div className="grid gap-4 md:grid-cols-2">
						<Field label="Foil" value={state.caseDraft.foil} onChange={(value) => setCaseField("foil", value)} />
						<Field label="Disaster" value={state.caseDraft.disaster} onChange={(value) => setCaseField("disaster", value)} multiline />
						<Field label="Key clues" value={state.caseDraft.key_clues.join("\n")} onChange={(value) => setCaseField("key_clues", value)} multiline />
						<Field label="Safe zone" value={state.caseDraft.safe_zone} onChange={(value) => setCaseField("safe_zone", value)} multiline />
						<Field label="Filing note" value={state.caseDraft.filing_note} onChange={(value) => setCaseField("filing_note", value)} multiline />
						<Field label="Student task" value={state.caseDraft.student_task} onChange={(value) => setCaseField("student_task", value)} multiline />
					</div>

					{errors.length > 0 ? <p role="alert" aria-live="polite" className="text-sm text-destructive">Fix inverse-thinking fields: {errors.join(", ")}</p> : null}

					<div className="flex flex-wrap gap-2">
						<Button type="button" variant="secondary" onClick={() => regenerate("field", "disaster")}>Regenerate field</Button>
						<Button type="button" variant="outline" onClick={() => regenerate("case")}>Regenerate case</Button>
						<Button type="button" variant="ghost" onClick={() => setState({ ...state, inspectorOpen: !state.inspectorOpen })}>Methodology inspector</Button>
					</div>

					<div className="rounded-lg border border-border bg-background p-3">
						<h3 className="font-medium">Student preview</h3>
						<iframe title="Inverse Thinking preview" srcDoc={renderedHtml} sandbox="allow-same-origin" className="mt-3 h-80 w-full rounded-md border border-border" />
					</div>

					{state.inspectorOpen ? <MethodologyInspector state={state} /> : null}
				</div>
			) : null}
		</section>
	);
}

function Field({ label, value, multiline = false, onChange }: { label: string; value: string; multiline?: boolean; onChange: (value: string) => void }) {
	return (
		<label className="space-y-2">
			<span className="text-sm font-medium">{label}</span>
			{multiline ? (
				<textarea className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={value} onChange={(event) => onChange(event.currentTarget.value)} />
			) : (
				<Input value={value} onChange={(event) => onChange(event.currentTarget.value)} />
			)}
		</label>
	);
}

function MethodologyInspector({ state }: { state: InverseThinkingEditorState }) {
	return (
		<aside className="rounded-lg border border-border bg-background p-4" aria-label="Methodology inspector">
			<h3 className="font-semibold">Methodology inspector</h3>
			<dl className="mt-3 grid gap-2 text-sm">
				<div><dt className="font-medium">Frame rationale</dt><dd>{state.creativeFrame}</dd></div>
				<div><dt className="font-medium">Disaster-first sequence</dt><dd>{state.caseDraft.disaster}</dd></div>
				<div><dt className="font-medium">Key clues</dt><dd>{state.caseDraft.key_clues.join(", ")}</dd></div>
				<div><dt className="font-medium">Safe-zone boundary</dt><dd>{state.caseDraft.safe_zone}</dd></div>
				<div><dt className="font-medium">Student task</dt><dd>{state.caseDraft.student_task}</dd></div>
			</dl>
			{state.qualityWarnings.length > 0 ? <ul className="mt-3 list-disc pl-5 text-sm text-amber-700">{state.qualityWarnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}
		</aside>
	);
}
