"use client";

import { ApprovalModal } from "@/components/approval-modal";
import { usePendingApprovals } from "@/hooks/use-approval";

export default function ApprovalsPage() {
	const { data: pendingApprovals, isLoading } = usePendingApprovals();

	if (isLoading)
		return <div className="text-muted-foreground">Loading approvals...</div>;

	return (
		<div>
			<h2 className="text-2xl font-bold">Pending Approvals</h2>
			<div className="mt-4 space-y-4">
				{pendingApprovals?.map((run) => (
					<ApprovalModal key={run.run_id} run={run} />
				))}
				{pendingApprovals?.length === 0 && (
					<p className="text-muted-foreground">No pending approvals.</p>
				)}
			</div>
		</div>
	);
}
