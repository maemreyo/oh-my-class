"use client";

import { motion } from "motion/react";
import { useState } from "react";
import { useApprove, useReject } from "@/hooks/use-approval";
import type { Run } from "@/types";

interface ApprovalModalProps {
	run: Run;
}

export function ApprovalModal({ run }: ApprovalModalProps) {
	const [feedback, setFeedback] = useState("");
	const approve = useApprove();
	const reject = useReject();

	return (
		<motion.div
			initial={{ opacity: 0, y: 10 }}
			animate={{ opacity: 1, y: 0 }}
			className="rounded-lg border border-border bg-card p-4"
		>
			<h3 className="font-semibold">{run.topic || `Run ${run.run_id}`}</h3>
			<p className="mt-1 text-sm text-muted-foreground">
				Step {run.current_step} — awaiting approval
			</p>

			<div className="mt-4 flex gap-2">
				<button
					type="button"
					onClick={() => approve.mutate(run.run_id)}
					disabled={approve.isPending}
					className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
				>
					Approve
				</button>
				<button
					type="button"
					onClick={() => {
						if (feedback.trim()) {
							reject.mutate({ runId: run.run_id, feedback });
						}
					}}
					disabled={reject.isPending || !feedback.trim()}
					className="rounded-md border border-destructive px-4 py-2 text-sm text-destructive hover:bg-destructive/10"
				>
					Reject
				</button>
			</div>

			<textarea
				value={feedback}
				onChange={(e) => setFeedback(e.target.value)}
				placeholder="Feedback for revision (required for rejection)..."
				className="mt-3 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
				rows={3}
			/>
		</motion.div>
	);
}
