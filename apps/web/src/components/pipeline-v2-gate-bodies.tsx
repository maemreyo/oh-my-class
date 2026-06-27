"use client";

import { useState } from "react";
import { snapshotPreviewUrl } from "@/hooks/use-pipeline-v2";
import type { ArtifactProgressItem, PipelineV2EventPayload, PipelineV2GateName } from "@/hooks/use-pipeline-v2";
import { PipelineV2ArtifactProgress } from "@/components/pipeline-v2-artifact-progress";

export function PipelineV2GateBody({ runId, gateName, event }: {
	readonly runId: string;
	readonly gateName: PipelineV2GateName;
	readonly event: PipelineV2EventPayload;
}) {
	switch (gateName) {
		case "clarification_required":
			return <QuestionList questions={event.questions ?? []} />;
		case "contract_confirmation":
			return <ContractSummary contract={event.contract} />;
		case "search_plan_confirmation":
			return <ReadableObject title="Search plan" value={event} />;
		case "blueprint_approval":
			return <ReadableObject title="Blueprint summary" value={event} />;
		case "content_approval":
			return <ContentApprovalBody runId={runId} snapshotIds={event.snapshot_ids ?? []} artifacts={event.artifacts ?? []} />;
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

function ContentApprovalBody({ runId, snapshotIds, artifacts }: {
	readonly runId: string;
	readonly snapshotIds: readonly string[];
	readonly artifacts: readonly ArtifactProgressItem[];
}) {
	return (
		<div className="space-y-4">
			{artifacts.length > 0 && <PipelineV2ArtifactProgress artifacts={artifacts} />}
			<ContentSnapshots runId={runId} snapshotIds={snapshotIds} />
		</div>
	);
}

function ContentSnapshots({ runId, snapshotIds }: { readonly runId: string; readonly snapshotIds: readonly string[] }) {
	const [view, setView] = useState<"student" | "teacher">("student");
	if (snapshotIds.length === 0) return <p className="text-sm text-muted-foreground">Preview snapshots are not ready yet.</p>;
	return (
		<div className="space-y-3">
			<div className="inline-flex rounded-md border border-border bg-background p-1" aria-label="Preview view">
				{(["student", "teacher"] as const).map((option) => (
					<button
						key={option}
						type="button"
						className={option === view ? "rounded bg-primary px-3 py-1 text-sm text-primary-foreground" : "px-3 py-1 text-sm text-muted-foreground"}
						onClick={() => setView(option)}
					>
						{option === "student" ? "Student view" : "Teacher view"}
					</button>
				))}
			</div>
			{snapshotIds.map((snapshotId) => (
				<iframe
					key={`${snapshotId}-${view}`}
					title={`${view === "student" ? "Student" : "Teacher"} preview ${snapshotId}`}
					src={snapshotPreviewUrl(runId, snapshotId, view)}
					className="h-80 w-full rounded-md border border-border bg-background"
					sandbox="allow-same-origin"
				/>
			))}
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
	if (value === null || value === undefined) return "Not set";
	return String(value);
}

function assertNever(value: never): never {
	throw new Error(`Unhandled gate: ${String(value)}`);
}
