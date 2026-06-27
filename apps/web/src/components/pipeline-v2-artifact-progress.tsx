"use client";

export interface ArtifactProgressItem {
	readonly artifact_id: string;
	readonly artifact_type: string;
	readonly status: "queued" | "generating" | "rendering" | "validating" | "ready" | "failed";
	readonly error?: string;
}

export interface PipelineV2ArtifactProgressProps {
	readonly artifacts: readonly ArtifactProgressItem[];
}

const STATUS_CONFIG = {
	queued: { label: "Queued", color: "text-muted-foreground" },
	generating: { label: "Generating", color: "text-blue-600" },
	rendering: { label: "Rendering", color: "text-amber-600" },
	validating: { label: "Validating", color: "text-amber-600" },
	ready: { label: "Ready", color: "text-green-600" },
	failed: { label: "Failed", color: "text-destructive" },
} as const;

export function PipelineV2ArtifactProgress({ artifacts }: PipelineV2ArtifactProgressProps) {
	if (artifacts.length === 0) return null;

	return (
		<section aria-labelledby="artifact-progress-title" className="rounded-lg border border-border bg-card p-4">
			<h2 id="artifact-progress-title" className="text-lg font-semibold">
				Artifact Progress
			</h2>
			<div className="mt-3 space-y-2">
				{artifacts.map((artifact) => {
					const config = STATUS_CONFIG[artifact.status];
					return (
						<div
							key={artifact.artifact_id}
							className="flex items-center justify-between rounded-md border border-border p-3"
						>
							<div className="flex items-center gap-3">
								<span className="text-sm font-medium">{artifact.artifact_type}</span>
								<span className="font-mono text-xs text-muted-foreground">{artifact.artifact_id}</span>
							</div>
							<div className="flex items-center gap-2">
								<span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
								{artifact.error && (
									<span className="text-xs text-destructive" title={artifact.error}>
										⚠
									</span>
								)}
							</div>
						</div>
					);
				})}
			</div>
		</section>
	);
}
