"use client";

import { Badge } from "@/components/ui/badge";

export interface TeachingPackStageProgressProps {
	readonly status: string;
}

const STAGES = [
	{ key: "pending", label: "Queued", detail: "Run accepted and waiting for a worker." },
	{ key: "running", label: "Running", detail: "Pipeline stages are producing the pack." },
	{ key: "awaiting_approval", label: "Teacher gate", detail: "A teacher decision is required." },
	{ key: "completed", label: "Completed", detail: "Artifacts are ready to export." },
] as const;

export function TeachingPackStageProgress({ status }: TeachingPackStageProgressProps) {
	return (
		<section aria-labelledby="teaching-packs-progress-title" className="rounded-lg border border-border bg-card p-4">
			<div className="flex items-center justify-between gap-4">
				<div>
					<h2 id="teaching-packs-progress-title" className="text-lg font-semibold">
						Teaching Pack progress
					</h2>
					<p className="text-sm text-muted-foreground">Persisted status with SSE replay after refresh.</p>
				</div>
				<Badge variant={status === "failed" ? "destructive" : "secondary"}>{status}</Badge>
			</div>
			<ol className="mt-4 grid gap-3 md:grid-cols-4">
				{STAGES.map((stage) => (
					<li key={stage.key} className={stageClass(stage.key, status)}>
						<p className="text-sm font-semibold">{stage.label}</p>
						<p className="mt-1 text-xs text-muted-foreground">{stage.detail}</p>
					</li>
				))}
			</ol>
		</section>
	);
}

function stageClass(stage: string, status: string): string {
	const active = stage === status || (stage === "awaiting_approval" && status.includes("approval"));
	return [
		"rounded-md border p-3 transition-colors",
		active ? "border-primary bg-primary/10" : "border-border bg-background",
	].join(" ");
}
