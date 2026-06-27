"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { PipelineV2GateShell } from "@/components/pipeline-v2-gate-shell";
import { PipelineV2StageProgress } from "@/components/pipeline-v2-stage-progress";
import { useRun } from "@/hooks/use-run";
import { usePipelineV2Status } from "@/hooks/use-pipeline-v2";
import type { PipelineV2EventPayload, PipelineV2StatusEvent } from "@/hooks/use-pipeline-v2";

export default function RunDetailPage() {
	const params = useParams();
	const runId = params.runId as string;

	const { data: run, error, isLoading } = useRun(runId);
	const { subscribe } = usePipelineV2Status(runId);
	const [v2Events, setV2Events] = useState<PipelineV2StatusEvent[]>([]);
	const [activeGate, setActiveGate] = useState<PipelineV2EventPayload | null>(null);

	useEffect(() => {
		const unsubscribe = subscribe((event) => {
			setV2Events((previous) => [...previous, event]);
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
					<p className="text-sm font-medium text-muted-foreground">Pipeline V2 run</p>
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
				<p className="text-sm font-medium text-muted-foreground">Pipeline V2 run</p>
				<h1 className="mt-1 text-3xl font-bold tracking-tight">{runId}</h1>
			</div>

			<PipelineV2StageProgress status={run?.status ?? "unknown"} />

			{activeGate ? (
				<PipelineV2GateShell
					runId={runId}
					event={activeGate}
					onResolved={() => setActiveGate(null)}
				/>
			) : null}

			<section aria-labelledby="pipeline-v2-events-title" className="rounded-lg border border-border bg-card p-4">
				<h2 id="pipeline-v2-events-title" className="text-lg font-semibold">Events</h2>
				<div className="mt-3 max-h-72 overflow-auto rounded-md bg-muted p-4 font-mono text-sm">
					{v2Events.length === 0 ? (
						<div className="text-muted-foreground">Waiting for events...</div>
					) : null}
					{v2Events.map((event, index) => (
						<div key={`v2-${event.name}-${index}`} className="border-b border-border py-2 last:border-b-0">
							<span className="text-primary">{event.name}</span>{" "}
							<span className="text-muted-foreground">{JSON.stringify(event.payload)}</span>
						</div>
					))}
				</div>
			</section>

			{run?.state && (
				<section aria-labelledby="pipeline-v2-state-title" className="rounded-lg border border-border bg-card p-4">
					<h2 id="pipeline-v2-state-title" className="text-lg font-semibold">Persisted state</h2>
					<pre className="mt-3 overflow-auto rounded-md bg-muted p-4 text-sm">
						{JSON.stringify(run.state, null, 2)}
					</pre>
				</section>
			)}
		</div>
	);
}

function isGateEvent(event: PipelineV2StatusEvent): boolean {
	return typeof event.payload.gate_id === "string" && (
		typeof event.payload.gate_name === "string" || typeof event.payload.gate === "string"
	);
}
