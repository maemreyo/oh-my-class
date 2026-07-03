import type { ArtifactExplanation } from "@/hooks/use-teaching-packs";

export function TeachingPackTrustPanel({
	autoApproved,
	revertWindowSeconds,
	explanations,
	onRevert,
	onRequestRevision,
}: {
	readonly autoApproved?: boolean;
	readonly revertWindowSeconds?: number;
	readonly explanations?: readonly ArtifactExplanation[];
	readonly onRevert?: () => void;
	readonly onRequestRevision?: (artifactId: string) => void;
}) {
	if (!autoApproved && (!explanations || explanations.length === 0)) return null;

	return (
		<div className="rounded-md border border-border bg-background p-4">
			<div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
				<div>
					<p className="text-sm font-semibold">
						{autoApproved ? "Auto-approved fast lane" : "Approval evidence"}
					</p>
					<p className="mt-1 text-sm text-muted-foreground">
						View details for the evidence used before this content reached the teacher gate.
					</p>
				</div>
				{revertWindowSeconds ? (
					<button
						type="button"
						className="rounded-full border border-border px-3 py-1 text-xs font-medium text-muted-foreground hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
						onClick={onRevert}
					>
						Revert available for {Math.round(revertWindowSeconds / 60)} minutes
					</button>
				) : null}
			</div>

			{explanations && explanations.length > 0 ? (
				<ul className="mt-3 space-y-2">
					{explanations.map((explanation) => (
						<li key={explanation.artifact_id} className="rounded-md bg-muted p-3 text-sm">
							<div className="flex items-center justify-between gap-3">
								<span className="font-medium capitalize">{explanation.artifact_type}</span>
								<span className="font-mono text-xs text-muted-foreground">
									Revision {explanation.revision_count}
								</span>
							</div>
							<p className="mt-1 text-muted-foreground">{explanation.judge_rationale}</p>
							{onRequestRevision ? (
								<button
									type="button"
									className="mt-2 text-sm font-medium text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-ring"
									onClick={() => onRequestRevision(explanation.artifact_id)}
								>
									Request revision
								</button>
							) : null}
						</li>
					))}
				</ul>
			) : null}
		</div>
	);
}
