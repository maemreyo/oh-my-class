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
							<span className="text-primary">{event.name}</span>{" "}
						<span className="break-all text-muted-foreground">{JSON.stringify(event.payload)}</span>
						</div>
					))}
				</div>
			</section>

		</div>
	);
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
