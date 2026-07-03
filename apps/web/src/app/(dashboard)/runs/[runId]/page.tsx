"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { TeachingPackGateShell } from "@/components/teaching-packs-gate-shell";
import { TeachingPackStageProgress } from "@/components/teaching-packs-stage-progress";
import { useTeachingPackRun, useTeachingPackStatus } from "@/hooks/use-teaching-packs";
import type { TeachingPackEventPayload, TeachingPackStatusEvent } from "@/hooks/use-teaching-packs";

export default function RunDetailPage() {
	const params = useParams();
	const runId = params.runId as string;

	const { data: run, error, isLoading } = useQuery(useTeachingPackRun(runId));
	const { subscribe } = useTeachingPackStatus(runId);
	const [teachingPackEvents, setTeachingPackEvents] = useState<TeachingPackStatusEvent[]>([]);
	const [activeGate, setActiveGate] = useState<TeachingPackEventPayload | null>(null);
	const escalated = hasEscalation(teachingPackEvents);

	useEffect(() => {
		const unsubscribe = subscribe((event) => {
			setTeachingPackEvents((previous) => [...previous, event]);
			if (isGateEvent(event)) setActiveGate(event.payload);
		});

		return unsubscribe;
	}, [subscribe]);

	if (isLoading) {
		return <div className="p-8 text-muted-foreground">Loading...</div>;
	}

	if (error) {
		return (
			<div className="mx-auto max-w-3xl p-4 md:p-8">
				<section aria-labelledby="gateway-unavailable-title" className="rounded-lg border border-border bg-card p-6 shadow-sm">
					<p className="text-sm font-medium text-muted-foreground">Teaching Pack run</p>
					<h1 id="gateway-unavailable-title" className="mt-2 text-2xl font-bold tracking-tight">
						Gateway unavailable
					</h1>
					<p className="mt-3 text-muted-foreground">
						The dashboard could not load run {runId}. Start the gateway service and refresh this page to resume monitoring.
					</p>
					<pre className="mt-4 overflow-auto rounded-md bg-muted p-4 text-sm text-muted-foreground">
						{error.message}
					</pre>
				</section>
			</div>
		);
	}

	return (
		<div className="mx-auto max-w-6xl space-y-6 p-4 md:p-8">
			<div>
				<p className="text-sm font-medium text-muted-foreground">Teaching Pack run</p>
				<h1 className="mt-1 break-all text-3xl font-bold tracking-tight">{runId}</h1>
			</div>

			<TeachingPackStageProgress status={run?.status ?? "unknown"} />

			{escalated ? (
				<section aria-labelledby="needs-review-title" className="rounded-lg border border-destructive/40 bg-destructive/10 p-4">
					<p className="text-sm font-medium text-destructive">Needs your review</p>
					<h2 id="needs-review-title" className="mt-1 text-xl font-semibold tracking-tight">A teaching pack issue needs a decision</h2>
					<p className="mt-2 text-sm text-muted-foreground">Review the current gate or request a focused artifact revision before export continues.</p>
					<a href="#teaching-packs-events-title" className="mt-3 inline-flex rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring">
						Review latest status
					</a>
				</section>
			) : null}

			{activeGate ? (
				<TeachingPackGateShell
					runId={runId}
					event={gateEventWithRunArtifactStatuses(activeGate, run?.artifact_statuses ?? [])}
					onResolved={() => setActiveGate(null)}
				/>
			) : null}

			<section aria-labelledby="teaching-packs-events-title" className="rounded-lg border border-border bg-card p-4">
				<h2 id="teaching-packs-events-title" className="text-lg font-semibold">Events</h2>
				<div className="mt-3 max-h-72 overflow-auto rounded-md bg-muted p-4 font-mono text-sm">
					{teachingPackEvents.length === 0 ? (
						<div className="text-muted-foreground">Waiting for events...</div>
					) : null}
					{teachingPackEvents.map((event, index) => (
						<div key={`teaching-pack-${event.name}-${index}`} className="border-b border-border py-2 last:border-b-0">
							<span className="text-primary">{teacherStatusLabel(event)}</span>
							<span className="block break-all text-muted-foreground">{teacherStatusDetail(event)}</span>
						</div>
					))}
				</div>
			</section>

		</div>
	);
}

export function teacherStatusLabel(event: TeachingPackStatusEvent): string {
	if (isEscalationEvent(event)) return "Needs your review";
	switch (event.name) {
		case "stage_transition":
			return stageTransitionLabel(event.payload);
		case "gate_decision":
			return "Teacher decision recorded";
		case "healing_decision":
			return "Content repair plan updated";
		case "breaker_tripped":
			return "Automatic retry paused";
		case "teaching_pack.run.accepted":
			return "Teaching pack run accepted";
		case "teaching_pack.artifact_workflow.status_changed":
			return artifactStatusLabel(event.payload);
		case "teaching_pack.content_approval.opened":
			return "Content is ready for approval";
		case "teaching_pack.blueprint_approval.opened":
			return "Blueprint is ready for approval";
		case "teaching_pack.clarification_required.opened":
			return "Clarification is needed";
		case "teaching_pack.contract_confirmation.opened":
			return "Teaching contract is ready to confirm";
		case "teaching_pack.search_plan_confirmation.opened":
			return "Research plan is ready to confirm";
		default:
			return "Teaching pack status updated";
	}
}

export function teacherStatusDetail(event: TeachingPackStatusEvent): string {
	const payload = eventPayload(event.payload);
	const reason = typeof payload.reason === "string" ? payload.reason : undefined;
	const stage = typeof payload.stage === "string" ? payload.stage.replaceAll("_", " ") : undefined;
	if (isEscalationEvent(event)) return reason ?? "The system needs a teacher decision before continuing.";
	if (stage) return `Stage: ${stage}`;
	return "No action needed right now.";
}

export function hasEscalation(events: readonly TeachingPackStatusEvent[]): boolean {
	return events.some(isEscalationEvent);
}

function isEscalationEvent(event: TeachingPackStatusEvent): boolean {
	const payload = eventPayload(event.payload);
	return event.name === "escalate" || event.name.includes("escalat") || payload.observability_event_type === "escalate";
}

function eventPayload(payload: TeachingPackEventPayload): TeachingPackEventPayload {
	const nested = payload.payload;
	if (nested !== null && typeof nested === "object" && !Array.isArray(nested)) {
		return { ...payload, ...Object.fromEntries(Object.entries(nested)) };
	}
	return payload;
}

function stageTransitionLabel(payload: TeachingPackEventPayload): string {
	const stage = typeof payload.stage === "string" ? payload.stage.replaceAll("_", " ") : "Pipeline";
	const status = typeof payload.status === "string" ? payload.status.replaceAll("_", " ") : "updated";
	return `${stage} ${status}`;
}

function artifactStatusLabel(payload: TeachingPackEventPayload): string {
	const artifactType = typeof payload.artifact_type === "string" ? payload.artifact_type : "artifact";
	const status = typeof payload.status === "string" ? payload.status : "updated";
	if (status === "escalated") return `${artifactType} needs teacher support`;
	return `${artifactType} ${status.replaceAll("_", " ")}`;
}

function isGateEvent(event: TeachingPackStatusEvent): boolean {
	return typeof event.payload.gate_id === "string" && (
		typeof event.payload.gate_name === "string" || typeof event.payload.gate === "string"
	);
}

export function gateEventWithRunArtifactStatuses(
	event: TeachingPackEventPayload,
	artifactStatuses: TeachingPackEventPayload["artifact_statuses"],
): TeachingPackEventPayload {
	if (event.artifact_statuses?.length || !artifactStatuses?.length) return event;
	return { ...event, artifact_statuses: artifactStatuses };
}
