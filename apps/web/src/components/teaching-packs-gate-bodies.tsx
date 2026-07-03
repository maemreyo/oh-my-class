"use client";

import type { TeachingPackEventPayload, TeachingPackGateName } from "@/hooks/use-teaching-packs";
import { ContentApprovalBody } from "@/components/teaching-packs-content-approval-body";

export function TeachingPackGateBody({ runId, gateName, event, onRevertFastLane, onRequestRevision }: {
	readonly runId: string;
	readonly gateName: TeachingPackGateName;
	readonly event: TeachingPackEventPayload;
	readonly onRevertFastLane?: (artifactId: string) => void;
	readonly onRequestRevision?: (artifactId: string) => void;
}) {
	switch (gateName) {
		case "clarification_required":
			return <QuestionList questions={event.questions ?? []} />;
		case "contract_confirmation":
			return <ContractSummary contract={event.contract} />;
		case "search_plan_confirmation":
			return <SearchPlanSummary event={event} />;
		case "blueprint_approval":
			return <BlueprintSummary event={event} />;
		case "unit_approval":
			return <UnitApprovalSummary event={event} />;
		case "content_approval":
			return <ContentApprovalBody runId={runId} event={event} onRevertFastLane={onRevertFastLane} onRequestRevision={onRequestRevision} />;
		default:
			return assertNever(gateName);
	}
}

function QuestionList({ questions }: { readonly questions: readonly Readonly<Record<string, unknown>>[] }) {
	if (questions.length === 0) return <p className="text-sm text-muted-foreground">No clarification questions were included.</p>;
	return (
		<ul className="space-y-2">
			{questions.map((question, index) => (
				<li key={`${String(question.field ?? "question")}-${index}`} className="rounded-md bg-background p-3 text-sm">
					<p className="font-medium">{String(question.field ?? `Question ${index + 1}`)}</p>
					<p className="text-muted-foreground">{String(question.prompt ?? "Please provide more detail.")}</p>
				</li>
			))}
		</ul>
	);
}

function ContractSummary({ contract }: { readonly contract: Readonly<Record<string, unknown>> | undefined }) {
	if (!contract) return <p className="text-sm text-muted-foreground">No contract payload was included.</p>;
	return (
		<dl className="grid gap-3 text-sm sm:grid-cols-2">
			{["topic", "grade_band", "subject", "locale", "artifact_types", "export_formats"].map((key) => (
				<div key={key} className="rounded-md bg-background p-3">
					<dt className="font-medium">{key.replaceAll("_", " ")}</dt>
					<dd className="mt-1 text-muted-foreground">{formatValue(contract[key])}</dd>
				</div>
			))}
		</dl>
	);
}

function SearchPlanSummary({ event }: { readonly event: TeachingPackEventPayload }) {
	const queryPlan = recordAt(event, "query_plan") ?? recordAt(event, "search_plan") ?? event;
	const queries = arrayAt(queryPlan, "queries");
	const sourcePolicy = recordAt(queryPlan, "source_policy") ?? recordAt(event, "source_policy");
	return (
		<div className="space-y-3 text-sm">
			<p className="font-medium">Research plan</p>
			<SummaryField label="Reason" value={queryPlan["reason"] ?? event["reason"]} />
			<SummaryField label="Estimated work" value={queryPlan["estimated_work"] ?? event["estimated_work"]} />
			<SummaryField label="Budget" value={queryPlan["budget"] ?? event["budget"]} />
			{queries.length > 0 ? (
				<div className="rounded-md bg-background p-3">
					<p className="font-medium">Queries</p>
					<ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
						{queries.map((query, index) => (
							<li key={`${String(query)}-${index}`}>{formatValue(query)}</li>
						))}
					</ul>
				</div>
			) : null}
			{sourcePolicy ? <ReadableObject title="Source policy" value={sourcePolicy} /> : null}
		</div>
	);
}

function BlueprintSummary({ event }: { readonly event: TeachingPackEventPayload }) {
	const blueprint = recordAt(event, "blueprint") ?? recordAt(event, "lesson_plan") ?? event;
	const objectives = arrayAt(blueprint, "learning_objectives");
	const checkpoints = arrayAt(blueprint, "assessment_checkpoints");
	return (
		<div className="space-y-3 text-sm">
			<p className="font-medium">Blueprint summary</p>
			<dl className="grid gap-3 sm:grid-cols-2">
				<SummaryField label="Topic" value={blueprint["topic"] ?? event["topic"]} />
				<SummaryField label="Grade" value={blueprint["grade_level"] ?? event["grade_level"]} />
				<SummaryField label="Subject" value={blueprint["subject"] ?? event["subject"]} />
				<SummaryField label="Duration" value={blueprint["duration_minutes"] ?? event["duration_minutes"]} />
			</dl>
			{objectives.length > 0 ? (
				<div className="rounded-md bg-background p-3">
					<p className="font-medium">Learning objectives</p>
					<ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
						{objectives.map((objective, index) => (
							<li key={`objective-${index}`}>{formatValue(objective)}</li>
						))}
					</ul>
				</div>
			) : null}
			{checkpoints.length > 0 ? (
				<div className="rounded-md bg-background p-3">
					<p className="font-medium">Assessment checkpoints</p>
					<ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
						{checkpoints.map((checkpoint, index) => (
							<li key={`checkpoint-${index}`}>{formatValue(checkpoint)}</li>
						))}
					</ul>
				</div>
			) : null}
		</div>
	);
}

function UnitApprovalSummary({ event }: { readonly event: TeachingPackEventPayload }) {
	const sequence = arrayAt(event, "lesson_sequence");
	return (
		<div className="space-y-3 text-sm">
			<p className="font-medium">Unit sequence</p>
			{sequence.length > 0 ? (
				<ul className="list-disc space-y-1 pl-5 text-muted-foreground">
					{sequence.map((lesson, index) => (
						<li key={`unit-lesson-${index}`}>{formatValue(lesson)}</li>
					))}
				</ul>
			) : (
				<ReadableObject title="Gate payload" value={event} />
			)}
		</div>
	);
}

function SummaryField({ label, value }: { readonly label: string; readonly value: unknown }) {
	return (
		<div className="rounded-md bg-background p-3">
			<dt className="font-medium">{label}</dt>
			<dd className="mt-1 text-muted-foreground">{formatValue(value)}</dd>
		</div>
	);
}

function ReadableObject({ title, value }: { readonly title: string; readonly value: Readonly<Record<string, unknown>> }) {
	return (
		<div>
			<p className="text-sm font-medium">{title}</p>
			<pre className="mt-2 max-h-72 overflow-auto rounded-md bg-background p-3 text-xs text-muted-foreground">
				{JSON.stringify(value, null, 2)}
			</pre>
		</div>
	);
}

function formatValue(value: unknown): string {
	if (Array.isArray(value)) return value.join(", ");
	if (value !== null && typeof value === "object") return Object.values(value).map(formatValue).join(" · ");
	if (value === null || value === undefined) return "Not set";
	return String(value);
}

function recordAt(source: Readonly<Record<string, unknown>>, key: string): Readonly<Record<string, unknown>> | null {
	const value = source[key];
	if (value !== null && typeof value === "object" && !Array.isArray(value)) return Object.fromEntries(Object.entries(value));
	return null;
}

function arrayAt(source: Readonly<Record<string, unknown>>, key: string): readonly unknown[] {
	const value = source[key];
	return Array.isArray(value) ? value : [];
}

function assertNever(value: never): never {
	throw new Error(`Unhandled gate: ${String(value)}`);
}
