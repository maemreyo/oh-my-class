"use client";

import { useState } from "react";
import { ApprovalModal } from "@/components/approval-modal";
import { usePendingApprovals } from "@/hooks/use-approval";

export default function ApprovalsPage() {
	const { data: pendingApprovals, isLoading } = usePendingApprovals();
	const [closedIds, setClosedIds] = useState<Set<string>>(new Set());

	if (isLoading)
		return <div className="text-muted-foreground">Loading approvals...</div>;

	const visible = (pendingApprovals ?? []).filter(
		(run) => !closedIds.has(run.run_id),
	);

	return (
		<div>
			<h2 className="text-2xl font-bold">Pending Approvals</h2>
			<div className="mt-4 space-y-4">
				{visible.map((run) => (
					<ApprovalModal
						key={run.run_id}
						runId={run.run_id}
						gateType="blueprint_approval"
						data={{}}
						onClose={() =>
							setClosedIds((prev) => new Set([...prev, run.run_id]))
						}
					/>
				))}
				{visible.length === 0 && (
					<p className="text-muted-foreground">No pending approvals.</p>
				)}
			</div>
		</div>
	);
}
