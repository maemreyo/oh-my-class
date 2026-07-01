import type { InputNormalizationReport } from "@oh-my-class/schemas";

export function VocabularyBatchNormalizationPreview({ report }: { report: InputNormalizationReport }) {
	return (
		<section aria-labelledby="vocabulary-normalization-title" className="grid gap-4 rounded-lg border bg-card p-6 text-card-foreground md:grid-cols-2">
			<div className="md:col-span-2">
				<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Vocabulary batch normalization</p>
				<h3 id="vocabulary-normalization-title" className="text-lg font-semibold">Input preview</h3>
				<p className="text-sm text-muted-foreground">Parse confidence {(report.parse_confidence * 100).toFixed(0)}%</p>
			</div>
			<div className="space-y-3 rounded-lg border bg-background p-4">
				<h4 className="text-sm font-semibold">Ready clusters</h4>
				{report.ready_clusters.length === 0 ? <p className="text-sm text-muted-foreground">No ready clusters yet.</p> : null}
				<ul className="space-y-3">
					{report.ready_clusters.map((cluster) => (
						<li key={cluster.cluster_id} className="rounded-md border bg-muted/40 p-3">
							<p className="text-sm font-medium">{cluster.title_hint ?? cluster.cluster_id}</p>
							<p className="text-sm text-muted-foreground">{cluster.terms.join(", ")}</p>
							{cluster.notes.length > 0 ? <p className="mt-2 text-xs text-muted-foreground">{cluster.notes.join(" · ")}</p> : null}
						</li>
					))}
				</ul>
			</div>
			<div className="space-y-3 rounded-lg border bg-background p-4">
				<h4 className="text-sm font-semibold">Ambiguous spans</h4>
				{report.ambiguous_clusters.length === 0 ? <p className="text-sm text-muted-foreground">No ambiguous spans.</p> : null}
				<ul className="space-y-3">
					{report.ambiguous_clusters.map((cluster) => (
						<li key={cluster.span_id} className="rounded-md border bg-muted/40 p-3">
							<p className="text-sm font-medium">{cluster.raw_input_span}</p>
							<p className="text-sm text-muted-foreground">{cluster.reason}</p>
						</li>
					))}
				</ul>
				{report.clarifying_questions.length > 0 ? (
					<div className="rounded-md bg-muted p-3">
						<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Clarifying questions</p>
						<ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-muted-foreground">
							{report.clarifying_questions.map((question) => <li key={question}>{question}</li>)}
						</ul>
					</div>
				) : null}
			</div>
		</section>
	);
}
