"use client";

import { useState } from "react";
import { useApproveRun, useRejectRun } from "@/hooks/use-approval";

interface ApprovalModalProps {
	runId: string;
	gateType: "blueprint_approval" | "content_approval";
	data: {
		lesson_plan?: Record<string, unknown>;
		artifacts?: Record<string, unknown>[];
		quality_scores?: Record<string, unknown>;
	};
	onClose: () => void;
	onApproved?: () => void;
	onRejected?: () => void;
}

export function ApprovalModal({
	runId,
	gateType,
	data,
	onClose,
	onApproved,
	onRejected,
}: ApprovalModalProps) {
	const [feedback, setFeedback] = useState("");
	const [activeTab, setActiveTab] = useState<"preview" | "feedback">("preview");

	const approveMutation = useApproveRun(runId);
	const rejectMutation = useRejectRun(runId);

	const handleApprove = async () => {
		await approveMutation.mutateAsync({ action: "approve" });
		onApproved?.();
		onClose();
	};

	const handleReject = async () => {
		if (!feedback.trim()) {
			alert("Feedback required for rejection");
			return;
		}
		await rejectMutation.mutateAsync({ feedback });
		onRejected?.();
		onClose();
	};

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
			<div className="max-h-[90vh] max-w-4xl overflow-hidden rounded-lg bg-white">
				{/* Header */}
				<div className="border-b p-4">
					<h2 className="text-xl font-semibold">
						{gateType === "blueprint_approval"
							? "Review Lesson Plan"
							: "Review Generated Content"}
					</h2>
				</div>

				{/* Tabs */}
				<div className="flex border-b">
					<button
						type="button"
						className={`px-4 py-2 ${activeTab === "preview" ? "border-b-2 border-blue-500" : ""}`}
						onClick={() => setActiveTab("preview")}
					>
						Preview
					</button>
					<button
						type="button"
						className={`px-4 py-2 ${activeTab === "feedback" ? "border-b-2 border-blue-500" : ""}`}
						onClick={() => setActiveTab("feedback")}
					>
						Feedback
					</button>
				</div>

				{/* Content */}
				<div className="max-h-[60vh] overflow-y-auto p-4">
					{activeTab === "preview" && (
						<div>
							{gateType === "blueprint_approval" && data.lesson_plan && (
								<pre className="overflow-auto rounded bg-gray-100 p-4">
									{JSON.stringify(data.lesson_plan, null, 2)}
								</pre>
							)}
							{gateType === "content_approval" && data.artifacts && (
								<div className="space-y-4">
									{data.artifacts.map((artifact, i) => (
										<div key={i} className="rounded border p-4">
											<h3 className="font-medium">
												{typeof artifact["title"] === "string"
													? artifact["title"]
													: `Artifact ${i + 1}`}
											</h3>
											<pre className="mt-2 overflow-auto rounded bg-gray-100 p-2 text-sm">
												{JSON.stringify(artifact, null, 2)}
											</pre>
										</div>
									))}
								</div>
							)}
						</div>
					)}

					{activeTab === "feedback" && (
						<div>
							<label className="mb-2 block font-medium">
								Feedback (required for rejection)
							</label>
							<textarea
								className="h-32 w-full rounded border p-2"
								value={feedback}
								onChange={(e) => setFeedback(e.target.value)}
								placeholder="Provide feedback for rejection..."
							/>
						</div>
					)}
				</div>

				{/* Footer */}
				<div className="flex justify-end gap-2 border-t p-4">
					<button
						type="button"
						className="rounded border px-4 py-2 hover:bg-gray-100"
						onClick={onClose}
					>
						Cancel
					</button>
					<button
						type="button"
						className="rounded bg-red-500 px-4 py-2 text-white hover:bg-red-600 disabled:opacity-50"
						onClick={handleReject}
						disabled={rejectMutation.isPending}
					>
						{rejectMutation.isPending ? "Rejecting..." : "Reject"}
					</button>
					<button
						type="button"
						className="rounded bg-green-500 px-4 py-2 text-white hover:bg-green-600 disabled:opacity-50"
						onClick={handleApprove}
						disabled={approveMutation.isPending}
					>
						{approveMutation.isPending ? "Approving..." : "Approve"}
					</button>
				</div>
			</div>
		</div>
	);
}
