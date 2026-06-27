"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useResumeTeachingPackRun } from "@/hooks/use-teaching-packs";
import type { TeachingPackEventPayload, TeachingPackGateName } from "@/hooks/use-teaching-packs";
import { TeachingPackGateBody } from "@/components/teaching-packs-gate-bodies";
import { TeachingPackScopedRejection } from "@/components/teaching-packs-scoped-rejection";
import type { ArtifactRejection } from "@/components/teaching-packs-scoped-rejection";

export interface TeachingPackGateShellProps {
	readonly runId: string;
	readonly event: TeachingPackEventPayload;
	readonly onResolved?: () => void;
}

export function TeachingPackGateShell({ runId, event, onResolved }: TeachingPackGateShellProps) {
	const gateName = gateNameFor(event);
	const gateId = typeof event.gate_id === "string" ? event.gate_id : "";
	const [feedback, setFeedback] = useState("");
	const [scopedRejectionMode, setScopedRejectionMode] = useState(false);
	const resume = useResumeTeachingPackRun(runId);

	if (!gateName || !gateId) return null;

	const submit = async (action: "approve" | "edit" | "reject") => {
		await resume.mutateAsync({
			gate_id: gateId,
			gate_name: gateName,
			action,
			response: feedback.trim() ? { feedback } : {},
		});
		onResolved?.();
	};

	const handleScopedRejection = async (rejections: readonly ArtifactRejection[]) => {
		await resume.mutateAsync({
			gate_id: gateId,
			gate_name: gateName,
			action: "reject",
			response: {
				rejection_type: "scoped",
				artifact_rejections: rejections,
			},
		});
		onResolved?.();
	};

	const showScopedRejection = gateName === "content_approval" && (event.artifacts?.length ?? 0) > 0;
	const artifacts = (event.artifacts ?? []).map((a) => ({ id: a.artifact_id, type: a.artifact_type }));

	return (
		<section aria-labelledby="teaching-packs-gate-title" className="rounded-lg border border-border bg-card p-6">
			<div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
				<div>
					<p className="text-xs font-semibold uppercase tracking-wide text-primary">Teacher gate</p>
					<h2 id="teaching-packs-gate-title" className="text-lg font-semibold">
						{labelFor(gateName)}
					</h2>
				</div>
				<p className="font-mono text-xs text-muted-foreground">{gateId}</p>
			</div>

			<div className="mt-4 rounded-md bg-muted p-4">
					<TeachingPackGateBody runId={runId} gateName={gateName} event={event} />
			</div>

			{scopedRejectionMode && showScopedRejection ? (
				<>
					<div className="mt-4 rounded-md bg-destructive/10 p-4">
						<TeachingPackScopedRejection
							artifacts={artifacts}
							onReject={handleScopedRejection}
							disabled={resume.isPending}
						/>
					</div>
					<button
						type="button"
						className="mt-2 text-sm text-muted-foreground hover:text-foreground"
						onClick={() => setScopedRejectionMode(false)}
					>
						← Back to general feedback
					</button>
				</>
			) : (
				<>
					<label className="mt-4 block text-sm font-medium" htmlFor="teaching-packs-gate-feedback">
						Feedback or edit notes
					</label>
					<textarea
						id="teaching-packs-gate-feedback"
						className="mt-2 min-h-24 w-full rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
						value={feedback}
						onChange={(event_) => setFeedback(event_.target.value)}
						placeholder="Tell the pipeline what to change, or leave blank to approve."
					/>
				</>
			)}

			{resume.error ? <p className="mt-3 text-sm text-destructive">{resume.error.message}</p> : null}

			<div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
				{showScopedRejection && !scopedRejectionMode ? (
					<button
						type="button"
						className="rounded-md border border-destructive px-4 py-2 text-sm text-destructive hover:bg-destructive/10"
						onClick={() => setScopedRejectionMode(true)}
					>
						Reject specific artifacts
					</button>
				) : null}
				{!scopedRejectionMode && (
					<>
						<Button type="button" variant="outline" disabled={resume.isPending} onClick={() => submit("reject")}>
							Reject
						</Button>
						<Button type="button" variant="secondary" disabled={resume.isPending} onClick={() => submit("edit")}>
							Request edits
						</Button>
						<Button type="button" disabled={resume.isPending} onClick={() => submit("approve")}>
							{resume.isPending ? "Submitting..." : "Approve"}
						</Button>
					</>
				)}
			</div>
		</section>
	);
}

function gateNameFor(event: TeachingPackEventPayload): TeachingPackGateName | null {
	const candidate = event.gate_name ?? event.gate;
	if (isGateName(candidate)) return candidate;
	return null;
}

function isGateName(value: unknown): value is TeachingPackGateName {
	switch (value) {
		case "clarification_required":
		case "contract_confirmation":
		case "search_plan_confirmation":
		case "blueprint_approval":
		case "content_approval":
			return true;
		default:
			return false;
	}
}

function labelFor(gateName: TeachingPackGateName): string {
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
		default:
			return assertNever(gateName);
	}
}

function assertNever(value: never): never {
	throw new Error(`Unhandled gate: ${String(value)}`);
}
