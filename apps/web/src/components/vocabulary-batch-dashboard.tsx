import type { SemanticAnchorCluster } from "@oh-my-class/schemas";

export type VocabularyBatchDashboardCluster = Pick<
	SemanticAnchorCluster,
	"cluster_id" | "title" | "terms" | "review_status" | "warnings"
> & {
	readonly exportedFiles?: readonly string[];
};

export type VocabularyBatchDashboardProps = {
	readonly clusters: readonly VocabularyBatchDashboardCluster[];
	readonly selectedClusterIds?: readonly string[];
};

const STATUS_LABELS = {
	passed: "Passed",
	needs_review: "Needs review",
	failed: "Failed",
} as const;

export function VocabularyBatchDashboard({ clusters, selectedClusterIds = [] }: VocabularyBatchDashboardProps) {
	const selected = new Set(selectedClusterIds);
	const counts = clusters.reduce(
		(acc, cluster) => ({
			...acc,
			[cluster.review_status]: acc[cluster.review_status] + 1,
		}),
		{ passed: 0, needs_review: 0, failed: 0 },
	);
	const exportableCount = clusters.filter((cluster) => cluster.review_status === "passed" || selected.has(cluster.cluster_id)).length;

	return (
		<section aria-labelledby="vocabulary-batch-dashboard-title" className="rounded-lg border bg-card p-6 text-card-foreground">
			<div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
				<div>
					<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Vocabulary batch rollout</p>
					<h3 id="vocabulary-batch-dashboard-title" className="text-lg font-semibold">Batch progress</h3>
					<p className="text-sm text-muted-foreground">{clusters.length} clusters · {exportableCount} currently exportable</p>
				</div>
				<div className="grid grid-cols-3 gap-2 text-center text-sm">
					<Stat label="Passed" value={counts.passed} />
					<Stat label="Needs review" value={counts.needs_review} />
					<Stat label="Failed" value={counts.failed} />
				</div>
			</div>
			<div className="mt-4 max-h-[520px] overflow-y-auto rounded-md border bg-background" aria-label="Cluster status navigation">
				{clusters.map((cluster, index) => {
					const selectedForExport = selected.has(cluster.cluster_id) || cluster.review_status === "passed";
					return (
						<article key={cluster.cluster_id} className="border-b p-3 last:border-b-0">
							<div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
								<div>
									<p className="text-xs font-semibold text-muted-foreground">Cluster {index + 1}</p>
									<h4 className="font-semibold">{cluster.title}</h4>
									<p className="text-sm text-muted-foreground">{cluster.terms.join(", ")}</p>
								</div>
								<div className="text-sm font-medium">{STATUS_LABELS[cluster.review_status]}</div>
							</div>
							{cluster.warnings.length > 0 ? <p className="mt-2 text-sm text-amber-700">{cluster.warnings.join(" · ")}</p> : null}
							<p className="mt-2 text-xs text-muted-foreground">{selectedForExport ? "Included in selected export" : "Withheld until review or excluded from selected export"}</p>
						</article>
					);
				})}
			</div>
		</section>
	);
}

function Stat({ label, value }: { readonly label: string; readonly value: number }) {
	return (
		<div className="rounded-md border bg-background p-2">
			<p className="text-lg font-semibold">{value}</p>
			<p className="text-xs text-muted-foreground">{label}</p>
		</div>
	);
}
