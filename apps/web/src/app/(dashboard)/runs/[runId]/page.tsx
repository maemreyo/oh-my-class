"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useRun, useRunStatus } from "@/hooks/use-run";
import { ApprovalModal } from "@/components/approval-modal";

export default function RunDetailPage() {
	const params = useParams();
	const runId = params.runId as string;

	const { data: run, isLoading } = useRun(runId);
	const { subscribe } = useRunStatus(runId);
	const [events, setEvents] = useState<string[]>([]);
	const [approvalGate, setApprovalGate] = useState<{
		type: "blueprint_approval" | "content_approval";
		data: Record<string, unknown>;
	} | null>(null);

	useEffect(() => {
		const unsubscribe = subscribe((event) => {
			try {
				const data = JSON.parse(event.data) as Record<string, unknown>;
				setEvents((prev) => [
					...prev,
					`${event.type}: ${JSON.stringify(data)}`,
				]);

				if (
					event.type === "interrupt" &&
					(data["gate"] === "blueprint_approval" ||
						data["gate"] === "content_approval")
				) {
					setApprovalGate({
						type: data["gate"] as "blueprint_approval" | "content_approval",
						data,
					});
				}
			} catch {
				// ignore unparseable SSE frames
			}
		});

		return unsubscribe;
	}, [subscribe]);

	if (isLoading) {
		return <div className="p-8 text-muted-foreground">Loading...</div>;
	}

	return (
		<div className="p-8">
			<h1 className="mb-4 text-2xl font-bold">Run: {runId}</h1>

			{/* Status */}
			<div className="mb-6">
				<span className="rounded bg-blue-100 px-2 py-1 text-blue-800">
					{run?.status ?? "Unknown"}
				</span>
			</div>

			{/* Events Log */}
			<div className="mb-6">
				<h2 className="mb-2 text-lg font-semibold">Events</h2>
				<div className="max-h-64 overflow-auto rounded bg-gray-100 p-4 font-mono text-sm">
					{events.length === 0 ? (
						<div className="text-gray-500">Waiting for events...</div>
					) : (
						events.map((event, i) => (
							<div key={i} className="border-b border-gray-200 py-1">
								{event}
							</div>
						))
					)}
				</div>
			</div>

			{/* Run State */}
			{run?.state && (
				<div>
					<h2 className="mb-2 text-lg font-semibold">State</h2>
					<pre className="overflow-auto rounded bg-gray-100 p-4 text-sm">
						{JSON.stringify(run.state, null, 2)}
					</pre>
				</div>
			)}

			{/* Approval Modal */}
			{approvalGate && (
				<ApprovalModal
					runId={runId}
					gateType={approvalGate.type}
					data={approvalGate.data}
					onClose={() => setApprovalGate(null)}
					onApproved={() => setApprovalGate(null)}
					onRejected={() => setApprovalGate(null)}
				/>
			)}
		</div>
	);
}
