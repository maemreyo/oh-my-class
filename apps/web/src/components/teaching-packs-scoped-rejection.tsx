"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export interface ArtifactRejection {
	readonly artifact_id: string;
	readonly reason: string;
}

export interface TeachingPackScopedRejectionProps {
	readonly artifacts: readonly { readonly id: string; readonly type: string }[];
	readonly onReject: (rejections: readonly ArtifactRejection[]) => Promise<void> | void;
	readonly disabled?: boolean;
}

export function TeachingPackScopedRejection({
	artifacts,
	onReject,
	disabled,
}: TeachingPackScopedRejectionProps) {
	const [rejections, setRejections] = useState<Map<string, string>>(new Map());
	const [isSubmitting, setIsSubmitting] = useState(false);

	const updateReason = (artifactId: string, reason: string) => {
		setRejections((prev) => {
			const next = new Map(prev);
			if (reason.trim()) {
				next.set(artifactId, reason);
			} else {
				next.delete(artifactId);
			}
			return next;
		});
	};

	const submit = async () => {
		const items: ArtifactRejection[] = [];
		for (const [artifactId, reason] of rejections) {
			items.push({ artifact_id: artifactId, reason });
		}
		setIsSubmitting(true);
		try {
			await onReject(items);
			setRejections(new Map());
		} finally {
			setIsSubmitting(false);
		}
	};

	const selectedCount = rejections.size;
	const canSubmit = selectedCount > 0 && !disabled && !isSubmitting;

	return (
		<div className="space-y-3">
			<p className="text-sm font-medium">Reject specific artifacts</p>
			{artifacts.length === 0 ? (
				<p className="text-sm text-muted-foreground">No artifacts to reject.</p>
			) : (
				<>
					{artifacts.map((artifact) => (
						<div key={artifact.id} className="flex items-start gap-3">
							<label
								className="mt-2 min-w-24 text-sm text-muted-foreground"
								htmlFor={`reject-${artifact.id}`}
							>
								{artifact.type}
							</label>
							<textarea
								id={`reject-${artifact.id}`}
								className="flex-1 rounded-md border border-input bg-background p-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
								placeholder={`Why reject ${artifact.type}?`}
								value={rejections.get(artifact.id) ?? ""}
								onChange={(e) => updateReason(artifact.id, e.target.value)}
								disabled={disabled || isSubmitting}
								rows={2}
							/>
						</div>
					))}
					{selectedCount > 0 && (
						<Button
							type="button"
							variant="destructive"
							onClick={submit}
							disabled={!canSubmit}
							className="mt-4"
						>
							{isSubmitting ? "Submitting..." : `Reject ${selectedCount} artifact${selectedCount > 1 ? "s" : ""}`}
						</Button>
					)}
				</>
			)}
		</div>
	);
}
