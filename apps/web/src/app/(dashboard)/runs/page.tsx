"use client";

import { RunCard } from "@/components/run-card";
import { useRuns } from "@/hooks/use-run";

export default function RunsPage() {
	const { data: runs, isLoading, error } = useRuns();

	if (isLoading)
		return <div className="text-muted-foreground">Loading runs...</div>;
	if (error) return <div className="text-destructive">Error loading runs</div>;

	return (
		<div>
			<h2 className="text-2xl font-bold">Teaching Pack Runs</h2>
			<div className="mt-4 grid gap-4">
				{runs?.map((run) => (
					<RunCard key={run.run_id} run={run} />
				))}
				{runs?.length === 0 && (
					<p className="text-muted-foreground">
						No runs yet. Create your first teaching pack!
					</p>
				)}
			</div>
		</div>
	);
}
