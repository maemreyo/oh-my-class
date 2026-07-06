"use client";

import { useState } from "react";
import { snapshotPreviewUrl } from "@/hooks/use-teaching-packs";
import type { TeachingPackEventPayload } from "@/hooks/use-teaching-packs";
import { TeachingPackArtifactProgress } from "@/components/teaching-packs-artifact-progress";
import { TeachingPacksSlideDeckPreview, type SlideDeckScopedFeedback, hasSlideDeckArtifact } from "@/components/teaching-packs-slide-deck-preview";
import { TeachingPackTrustPanel } from "@/components/teaching-packs-trust-panel";

export function ContentApprovalBody({ runId, event, onRevertFastLaneAction, onRequestRevisionAction, onSlideDeckFeedbackAction }: {
	readonly runId: string;
	readonly event: TeachingPackEventPayload;
	readonly onRevertFastLaneAction?: (artifactId: string) => void;
	readonly onRequestRevisionAction?: (artifactId: string) => void;
	readonly onSlideDeckFeedbackAction?: (feedback: SlideDeckScopedFeedback) => void | Promise<void>;
}) {
	const artifacts = event.artifact_statuses ?? event.artifacts ?? [];
	return (
		<div className="space-y-4">
			<TeachingPackTrustPanel
				autoApproved={event.auto_approved}
				trustScore={event.trust_score}
				revertWindowSeconds={event.revert_window_seconds}
				explanations={event.artifact_explanations}
				onRevert={() => {
					const artifactId = event.artifact_explanations?.[0]?.artifact_id;
					if (artifactId) onRevertFastLaneAction?.(artifactId);
				}}
				onRequestRevision={onRequestRevisionAction}
			/>
			{artifacts.length > 0 && <TeachingPackArtifactProgress artifacts={artifacts} />}
			<QualityFlagsPanel qualityScores={event.quality_scores} />
			{hasSlideDeckArtifact(event) ? (
				<TeachingPacksSlideDeckPreview runId={runId} event={event} onSubmitFeedbackAction={onSlideDeckFeedbackAction} />
			) : null}
			<ContentSnapshots runId={runId} snapshotIds={event.snapshot_ids ?? []} />
		</div>
	);
}

const FAILURE_CLASS_LABELS: Readonly<Record<string, string>> = {
	factual_uncertainty: "Facts",
	pedagogical_mismatch: "Pedagogy / Age",
	pii_leakage: "PII",
	external_asset: "HTML assets",
	missing_doctype: "HTML structure",
	answer_key_leakage: "Answer-key safety",
	schema_invalid: "Schema",
	placeholder_content: "Placeholder content",
	unsupported_component: "Component type",
	export_not_ready: "Export readiness",
};

interface QualityIssueShape {
	readonly failure_class: string;
	readonly location: string;
	readonly message: string;
	readonly hard_block?: boolean;
}

interface QualityReportShape {
	readonly artifact_id: string;
	readonly artifact_type: string;
	readonly passed: boolean;
	readonly issues?: readonly QualityIssueShape[];
}

function parseReports(qualityScores: unknown): readonly QualityReportShape[] {
	if (!qualityScores || typeof qualityScores !== "object") return [];
	const scores = qualityScores as Readonly<Record<string, unknown>>;
	if (!Array.isArray(scores.reports)) return [];
	return scores.reports.filter(
		(report): report is QualityReportShape =>
			report !== null && typeof report === "object" && typeof report.artifact_id === "string",
	);
}

function QualityFlagsPanel({ qualityScores }: { readonly qualityScores?: unknown }) {
	const [expanded, setExpanded] = useState(false);
	const reports = parseReports(qualityScores);
	if (reports.length === 0) return null;

	const allPassed = reports.every((report) => report.passed);

	return (
		<div className="rounded-md border border-border bg-background">
			<button
				type="button"
				className="flex w-full items-center justify-between px-4 py-3 text-left text-sm"
				onClick={() => setExpanded((value) => !value)}
				aria-expanded={expanded}
			>
				<span className="font-medium">
					Quality check results
					{allPassed ? (
						<span className="ml-2 inline-flex items-center rounded-full border border-border bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
							All passed
						</span>
					) : (
						<span className="ml-2 inline-flex items-center rounded-full border border-border bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
							Issues found
						</span>
					)}
				</span>
				<span className="text-muted-foreground">{expanded ? "Collapse" : "View details"}</span>
			</button>

			{expanded ? (
				<div className="space-y-3 border-t border-border px-4 pb-4 pt-3">
					{reports.map((report) => (
						<div key={report.artifact_id} className="rounded-md bg-muted p-3">
							<div className="mb-2 flex items-center gap-2">
								<span className={report.passed ? "inline-block h-2 w-2 rounded-full bg-primary" : "inline-block h-2 w-2 rounded-full bg-destructive"} />
								<span className="text-xs font-medium uppercase text-muted-foreground">
									{report.artifact_type}
								</span>
								<span className="font-mono text-xs text-muted-foreground">{report.artifact_id.slice(0, 12)}…</span>
							</div>
							{report.passed ? (
								<p className="text-xs text-muted-foreground">All quality layers passed.</p>
							) : (
								<ul className="space-y-1">
									{(report.issues ?? []).map((issue, index) => (
										<li key={`${issue.failure_class}-${index}`} className="text-xs">
											<span className="font-medium text-destructive">
												{FAILURE_CLASS_LABELS[issue.failure_class] ?? issue.failure_class}
											</span>
											{" — "}
											<span className="text-muted-foreground">{issue.message}</span>
										</li>
									))}
								</ul>
							)}
						</div>
					))}
				</div>
			) : null}
		</div>
	);
}

function ContentSnapshots({ runId, snapshotIds }: { readonly runId: string; readonly snapshotIds: readonly string[] }) {
	const [view, setView] = useState<"student" | "teacher" | "print">("student");
	if (snapshotIds.length === 0) return <p className="text-sm text-muted-foreground">Preview snapshots are not ready yet.</p>;
	return (
		<div className="space-y-3">
			<div className="inline-flex rounded-md border border-border bg-background p-1" aria-label="Preview view">
				{(["student", "teacher", "print"] as const).map((option) => (
					<button
						key={option}
						type="button"
						className={option === view ? "rounded bg-primary px-3 py-1 text-sm text-primary-foreground" : "px-3 py-1 text-sm text-muted-foreground"}
						onClick={() => setView(option)}
					>
						{option === "student" ? "Student view" : option === "teacher" ? "Teacher view" : "Print view"}
					</button>
				))}
			</div>
			{snapshotIds.map((snapshotId) => (
				<iframe
					key={`${snapshotId}-${view}`}
					title={`${view === "student" ? "Student" : "Teacher"} preview ${snapshotId}`}
					src={snapshotPreviewUrl(runId, snapshotId, view)}
					className="h-80 w-full rounded-md border border-border bg-background"
					sandbox="allow-same-origin"
				/>
			))}
		</div>
	);
}
