import type { ArtifactExplanation } from "@/hooks/use-teaching-packs";

export function TeachingPackTrustPanel({
	autoApproved,
	trustScore,
	revertWindowSeconds,
	explanations,
	onRevert,
	onRequestRevision,
}: {
	readonly autoApproved?: boolean;
	readonly trustScore?: number;
	readonly revertWindowSeconds?: number;
	readonly explanations?: readonly ArtifactExplanation[];
	readonly onRevert?: () => void;
	readonly onRequestRevision?: (artifactId: string) => void;
}) {
	if (!autoApproved && trustScore === undefined && (!explanations || explanations.length === 0)) return null;

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

			{trustScore !== undefined ? (
				<div className="mt-3 rounded-md bg-muted p-3 text-sm">
					<div className="flex items-center justify-between gap-3">
						<span className="font-medium">Teacher trust score</span>
						<span className="font-mono text-xs text-muted-foreground">
							{Math.round(trustScore * 100)}%
						</span>
					</div>
					<p className="mt-1 text-muted-foreground">
						Computed from this teacher&apos;s recent content approval decisions.
					</p>
				</div>
			) : null}

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
							{explanation.healing_history.length > 0 ? (
								<div className="mt-2 rounded-md border border-border bg-background p-2">
									<p className="text-xs font-medium text-muted-foreground">Healing history</p>
									<ul className="mt-1 space-y-1">
										{explanation.healing_history.map((entry, index) => (
											<li key={`${explanation.artifact_id}-healing-${index}`} className="text-xs text-muted-foreground">
												{healingHistoryLabel(entry)}
											</li>
										))}
									</ul>
								</div>
							) : null}
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

function healingHistoryLabel(entry: Readonly<Record<string, unknown>>): string {
	const strategy = stringField(entry, "strategy") ?? stringField(entry, "healing_strategy") ?? "healing";
	const note = stringField(entry, "note") ?? stringField(entry, "healing_note");
	return note ? `${strategy}: ${note}` : strategy;
}

function stringField(record: Readonly<Record<string, unknown>>, key: string): string | null {
	const value = record[key];
	return typeof value === "string" && value.length > 0 ? value : null;
}
