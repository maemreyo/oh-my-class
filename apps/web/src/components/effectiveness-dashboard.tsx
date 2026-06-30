import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type EffectivenessMetric = {
	readonly label: string;
	readonly value: string;
	readonly helper: string;
};

export type EffectivenessDashboardProps = {
	readonly averageMastery: string;
	readonly percentDat: string;
	readonly trend: string;
};

export function EffectivenessDashboard({
	averageMastery,
	percentDat,
	trend,
}: EffectivenessDashboardProps) {
	const metrics: readonly EffectivenessMetric[] = [
		{
			label: "Average mastery",
			value: averageMastery,
			helper: "Class-level KC mastery, aggregated across consenting learners.",
		},
		{
			label: "% đạt",
			value: percentDat,
			helper: "Share of learners currently meeting the selected mastery threshold.",
		},
		{
			label: "Trend",
			value: trend,
			helper: "Directional change since the previous outcome snapshot.",
		},
	] as const;

	return (
		<section className="grid gap-6" aria-labelledby="effectiveness-title">
			<div className="grid gap-2">
				<Badge variant="secondary" className="w-fit">
					Advisory aggregate
				</Badge>
				<h2 id="effectiveness-title" className="text-2xl font-bold tracking-tight">
					Effectiveness loop
				</h2>
				<p className="max-w-3xl text-sm leading-6 text-muted-foreground">
					Use this view to improve future teaching packs. These signals stay aggregated, advisory, and scoped to planning next steps.
				</p>
			</div>

			<div className="grid gap-4 md:grid-cols-3">
				{metrics.map((metric) => (
					<Card key={metric.label}>
						<CardHeader className="pb-3">
							<CardTitle className="text-lg">{metric.label}</CardTitle>
						</CardHeader>
						<CardContent className="grid gap-3">
							<p className="font-mono text-3xl font-bold text-primary">{metric.value}</p>
							<p className="text-sm leading-6 text-muted-foreground">{metric.helper}</p>
						</CardContent>
					</Card>
				))}
			</div>

			<Card>
				<CardHeader>
					<CardTitle className="text-lg">Honesty guardrails</CardTitle>
				</CardHeader>
				<CardContent>
					<ul className="grid gap-3 text-sm leading-6 text-muted-foreground">
						<li>Signals stay aggregate and advisory.</li>
						<li>Cold-start mastery falls back to persona and class knowledge history.</li>
						<li>No unverified composite formula or marketing statistic is used.</li>
					</ul>
				</CardContent>
			</Card>
		</section>
	);
}
