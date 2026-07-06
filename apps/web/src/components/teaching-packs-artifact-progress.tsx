"use client";

export interface ArtifactProgressItem {
	readonly artifact_id: string;
	readonly artifact_type: string;
	readonly status: "queued" | "generating" | "rendering" | "validating" | "ready" | "failed" | "passed" | "regenerating" | "skipped_due_dependency" | "escalated";
	readonly summary?: string;
	readonly teacher_action?: string;
	readonly error?: string;
}

export function labelForArtifactType(artifactType: string): string {
	return artifactType === "slide_deck" ? "Slide deck" : artifactType.replaceAll("_", " ");
}

export interface TeachingPackArtifactProgressProps {
	readonly artifacts: readonly ArtifactProgressItem[];
}

const STATUS_CONFIG = {
	queued: { label: "Queued", color: "text-muted-foreground" },
	generating: { label: "Generating", color: "text-blue-600" },
	regenerating: { label: "Regenerating", color: "text-blue-600" },
	rendering: { label: "Rendering", color: "text-amber-600" },
	validating: { label: "Validating", color: "text-amber-600" },
	ready: { label: "Ready", color: "text-green-600" },
	passed: { label: "Passed", color: "text-green-600" },
	failed: { label: "Failed", color: "text-destructive" },
	skipped_due_dependency: { label: "Skipped due dependency", color: "text-amber-600" },
	escalated: { label: "Escalated", color: "text-destructive" },
} as const;

export function TeachingPackArtifactProgress({ artifacts }: TeachingPackArtifactProgressProps) {
	if (artifacts.length === 0) return null;

	return (
		<section aria-labelledby="artifact-progress-title" className="rounded-lg border border-border bg-card p-4">
			<h2 id="artifact-progress-title" className="text-lg font-semibold">
				Artifact status
			</h2>
			<div className="mt-3 space-y-2">
				{artifacts.map((artifact) => {
					const config = STATUS_CONFIG[artifact.status];
					return (
						<div
							key={artifact.artifact_id}
							className="rounded-md border border-border bg-background p-3"
						>
							<div className="flex items-start justify-between gap-3">
								<div>
									<p className="text-sm font-medium">{labelForArtifactType(artifact.artifact_type)}</p>
									<p className="font-mono text-xs text-muted-foreground">{artifact.artifact_id}</p>
								</div>
								<span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
							</div>
							{artifact.summary ? <p className="mt-2 text-sm text-muted-foreground">{artifact.summary}</p> : null}
							{artifact.teacher_action ? <p className="mt-1 text-sm font-medium">{artifact.teacher_action}</p> : null}
							{artifact.error ? <p className="mt-1 text-xs text-destructive">{artifact.error}</p> : null}
						</div>
					);
				})}
			</div>
		</section>
	);
}
