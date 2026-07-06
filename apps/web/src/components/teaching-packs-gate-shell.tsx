"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useRequestArtifactRevision, useResumeTeachingPackRun } from "@/hooks/use-teaching-packs";
import type { TeachingPackEventPayload, TeachingPackGateAction } from "@/hooks/use-teaching-packs";
import { TeachingPackGateBody } from "@/components/teaching-packs-gate-bodies";
import { editableArtifactsFor, gateNameFor, labelFor, responseFor, strategyFeedbackResponse } from "@/components/teaching-packs-gate-shell-utils";
import { TeachingPackScopedRejection, TeachingPackSectionEditor } from "@/components/teaching-packs-scoped-rejection";
import type { ArtifactRejection, ContentSectionEdit } from "@/components/teaching-packs-scoped-rejection";
import type { StrategyFeedbackDraft } from "@/components/teaching-packs-strategy-panel";

export interface TeachingPackGateShellProps {
	readonly runId: string;
	readonly event: TeachingPackEventPayload;
	readonly onResolved?: () => void;
}

export function TeachingPackGateShell({ runId, event, onResolved }: TeachingPackGateShellProps) {
	const gateName = gateNameFor(event);
	const gateId = typeof event.gate_id === "string" ? event.gate_id : "";
	const [feedback, setFeedback] = useState("");
	const [scopedRejectionMode, setScopedRejectionMode] = useState(false);
	const [sectionEditorMode, setSectionEditorMode] = useState(false);
	const resume = useResumeTeachingPackRun(runId);
	const revision = useRequestArtifactRevision(runId);

	if (!gateName || !gateId) return null;

	const submit = async (action: TeachingPackGateAction) => {
		await resume.mutateAsync({
			gate_id: gateId,
			gate_name: gateName,
			action,
			response: responseFor(gateName, feedback),
		});
		onResolved?.();
	};

	const handleScopedRejection = async (rejections: readonly ArtifactRejection[]) => {
		await resume.mutateAsync({
			gate_id: gateId,
			gate_name: gateName,
				action: "reject_selected",
			response: {
				rejection_type: "scoped",
				artifact_rejections: rejections,
			},
		});
		onResolved?.();
	};

	const handleSectionEdit = async (edit: ContentSectionEdit) => {
		await resume.mutateAsync({
			gate_id: gateId,
			gate_name: gateName,
			action: "edit",
			response: {
				edit_type: "scoped_section",
				versioning: "new_content_snapshot",
				section_edit: edit,
			},
		});
		onResolved?.();
	};

	const handleStrategyFeedback = async (draft: StrategyFeedbackDraft) => {
		await resume.mutateAsync({
			gate_id: gateId,
			gate_name: gateName,
			action: "edit",
			response: strategyFeedbackResponse(draft),
		});
		onResolved?.();
	};

	const rejectionSourceArtifacts = event.artifact_statuses ?? event.artifacts ?? [];
	const showScopedRejection = gateName === "content_approval" && rejectionSourceArtifacts.length > 0;
	const artifacts = editableArtifactsFor(event, rejectionSourceArtifacts);
	const showSectionEditor = gateName === "content_approval" && artifacts.some((artifact) => artifact.sections && artifact.sections.length > 0);
	const showEscalatedBadge = event.escalated === true || event.needs_review === true || event.approval_mode === "manual_required";

	return (
		<section aria-labelledby="teaching-packs-gate-title" className="rounded-lg border border-border bg-card p-6">
			<div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
				<div>
					<p className="text-xs font-semibold uppercase tracking-wide text-primary">Teacher gate</p>
					<h2 id="teaching-packs-gate-title" className="text-lg font-semibold">
						{labelFor(gateName)}
					</h2>
					{showEscalatedBadge ? (
						<p className="mt-2 inline-flex rounded-full border border-destructive px-2 py-1 text-xs font-semibold text-destructive">
							Needs your review
						</p>
					) : null}
				</div>
				<p className="break-all font-mono text-xs text-muted-foreground">{gateId}</p>
			</div>

			<div className="mt-4 rounded-md bg-muted p-4">
					<TeachingPackGateBody
						runId={runId}
						gateName={gateName}
						event={event}
						onRevertFastLaneAction={(artifactId) => revision.mutate({ artifact_id: artifactId, feedback: "Revert fast-lane auto-approval." })}
						onRequestRevisionAction={(artifactId) => revision.mutate({ artifact_id: artifactId, feedback: "Teacher requested a post-export revision." })}
						onStrategyFeedbackAction={handleStrategyFeedback}
					/>
			</div>

				{sectionEditorMode && showSectionEditor ? (
					<>
						<div className="mt-4 rounded-md bg-muted p-4">
							<TeachingPackSectionEditor
								artifacts={artifacts}
								onSubmit={handleSectionEdit}
								disabled={resume.isPending}
							/>
						</div>
						<button
							type="button"
							className="mt-2 text-sm text-muted-foreground hover:text-foreground"
							onClick={() => setSectionEditorMode(false)}
						>
							Back to general feedback
						</button>
					</>
				) : scopedRejectionMode && showScopedRejection ? (
					<>
					<div className="mt-4 rounded-md bg-destructive/10 p-4">
						<TeachingPackScopedRejection
							artifacts={artifacts}
							onReject={handleScopedRejection}
							disabled={resume.isPending}
						/>
					</div>
					<button
						type="button"
						className="mt-2 text-sm text-muted-foreground hover:text-foreground"
						onClick={() => setScopedRejectionMode(false)}
					>
						← Back to general feedback
					</button>
				</>
			) : (
				<>
					<label className="mt-4 block text-sm font-medium" htmlFor="teaching-packs-gate-feedback">
						{gateName === "clarification_required" ? "Clarification answer" : "Feedback or edit notes"}
					</label>
					<textarea
						id="teaching-packs-gate-feedback"
						className="mt-2 min-h-24 w-full rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
						value={feedback}
						onChange={(event_) => setFeedback(event_.target.value)}
						placeholder={gateName === "clarification_required" ? "Answer the clarification questions." : "Tell the pipeline what to change, or leave blank to approve."}
					/>
				</>
			)}

				{resume.error ? <p className="mt-3 text-sm text-destructive">{resume.error.message}</p> : null}

				<div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
					{showSectionEditor && !sectionEditorMode && !scopedRejectionMode ? (
						<button
							type="button"
							className="rounded-md border border-border px-4 py-2 text-sm text-foreground hover:bg-muted"
							onClick={() => setSectionEditorMode(true)}
						>
							Edit a section
						</button>
					) : null}
					{showScopedRejection && !scopedRejectionMode && !sectionEditorMode ? (
						<button
						type="button"
						className="rounded-md border border-destructive px-4 py-2 text-sm text-destructive hover:bg-destructive/10"
						onClick={() => setScopedRejectionMode(true)}
					>
						Reject specific artifacts
					</button>
				) : null}
						{!scopedRejectionMode && !sectionEditorMode && gateName === "clarification_required" ? (
						<Button type="button" disabled={resume.isPending} onClick={() => submit("answer")}>
							{resume.isPending ? "Submitting..." : "Submit answer"}
						</Button>
					) : null}
						{!scopedRejectionMode && !sectionEditorMode && gateName !== "clarification_required" ? (
						<>
							<Button type="button" variant="outline" disabled={resume.isPending} onClick={() => submit("reject")}>
								Reject
							</Button>
							<Button type="button" variant="secondary" disabled={resume.isPending} onClick={() => submit("edit")}>
								Request edits
							</Button>
							<Button type="button" disabled={resume.isPending} onClick={() => submit("approve")}>
								{resume.isPending ? "Submitting..." : "Approve"}
							</Button>
						</>
					) : null}
				</div>
		</section>
	);
}
