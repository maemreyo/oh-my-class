"use client";

import { useMemo, useState } from "react";
import { RunCard } from "@/components/run-card";
import { Input } from "@/components/ui/input";
import { useRuns } from "@/hooks/use-run";
import {
	ALL_ARTIFACT_TYPES,
	collectArtifactTypes,
	filterRuns,
} from "./filter-runs";

export default function RunsPage() {
	const { data: runs, isLoading, error } = useRuns();
	const [keyword, setKeyword] = useState("");
	const [artifactType, setArtifactType] = useState(ALL_ARTIFACT_TYPES);

	// ponytail: no date field exists on Run (see common/schemas/src/run.ts) and
	// adding one is a backend change out of scope for this issue — AC allows
	// date-range "and/or" artifact-type, so artifact-type covers it.
	const artifactTypes = useMemo(() => collectArtifactTypes(runs ?? []), [runs]);
	const filteredRuns = useMemo(
		() => filterRuns(runs ?? [], { keyword, artifactType }),
		[runs, keyword, artifactType],
	);

	if (isLoading)
		return <div className="text-muted-foreground">Loading runs...</div>;
	if (error) return <div className="text-destructive">Error loading runs</div>;

	const hasRuns = (runs?.length ?? 0) > 0;

	return (
		<div>
			<h2 className="text-2xl font-bold">Teaching Pack Runs</h2>
			{hasRuns && (
				<div className="mt-4 flex flex-wrap gap-2">
					<Input
						placeholder="Search by title..."
						value={keyword}
						onChange={(e) => setKeyword(e.target.value)}
						className="max-w-xs"
						aria-label="Search runs by title"
					/>
					<select
						value={artifactType}
						onChange={(e) => setArtifactType(e.target.value)}
						aria-label="Filter by artifact type"
						className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					>
						<option value={ALL_ARTIFACT_TYPES}>All artifact types</option>
						{artifactTypes.map((type) => (
							<option key={type} value={type}>
								{type}
							</option>
						))}
					</select>
				</div>
			)}
			<div className="mt-4 grid gap-4">
				{filteredRuns.map((run) => (
					<RunCard key={run.run_id} run={run} />
				))}
				{!hasRuns && (
					<p className="text-muted-foreground">
						No runs yet. Create your first teaching pack!
					</p>
				)}
				{hasRuns && filteredRuns.length === 0 && (
					<p className="text-muted-foreground">
						No runs match your filters. Try a different keyword or artifact
						type.
					</p>
				)}
			</div>
		</div>
	);
}
