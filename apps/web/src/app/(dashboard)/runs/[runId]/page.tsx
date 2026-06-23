"use client";

import { useParams } from "next/navigation";
import { ArtifactPreview } from "@/components/artifact-preview";
import { useArtifacts } from "@/hooks/use-artifact";
import { useRun } from "@/hooks/use-run";

export default function RunDetailPage() {
	const params = useParams();
	const runId = params.runId as string;

	const { data: run, isLoading } = useRun(runId);
	const { data: artifacts } = useArtifacts(runId);

	if (isLoading)
		return <div className="text-muted-foreground">Loading run...</div>;
	if (!run) return <div>Run not found</div>;

	return (
		<div>
			<h2 className="text-2xl font-bold">{run.topic || `Run ${runId}`}</h2>
			<p className="text-muted-foreground">
				Status: {run.status} | Step: {run.current_step}/13
			</p>

			<div className="mt-6 space-y-4">
				{artifacts?.map((artifact) => (
					<ArtifactPreview key={artifact.artifact_id} artifact={artifact} />
				))}
			</div>
		</div>
	);
}
