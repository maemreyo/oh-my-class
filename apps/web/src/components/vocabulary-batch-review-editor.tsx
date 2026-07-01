"use client";

import { useMemo, useState } from "react";
import type { PracticeSet, SemanticAnchorCluster } from "@oh-my-class/schemas";
import { SemanticAnchorClusterSchema } from "@oh-my-class/schemas";

export type VocabularyReviewAction = "approve" | "regenerate" | "skip";

export type VocabularyPreferenceEvent = {
	readonly clusterId: string;
	readonly fieldPath: string;
	readonly previousValue: string;
	readonly nextValue: string;
};

export type VocabularyReviewDecision = {
	readonly action: VocabularyReviewAction;
	readonly cluster: SemanticAnchorCluster;
	readonly preferenceEvents: readonly VocabularyPreferenceEvent[];
	readonly unlockStudentExport: boolean;
};

export type VocabularyBatchReviewEditorProps = {
	readonly clusters: readonly SemanticAnchorCluster[];
	readonly practiceSets: readonly PracticeSet[];
	readonly onDecisionAction?: (decision: VocabularyReviewDecision) => void;
};

type EditableClusterField = "title" | "summary_rows.0" | "contrast_notes.0";

function practiceCount(practiceSets: readonly PracticeSet[], clusterId: string): number {
	return practiceSets.find((set) => set.cluster_id === clusterId)?.items.length ?? 0;
}

function fieldValue(cluster: SemanticAnchorCluster, field: EditableClusterField): string {
	switch (field) {
		case "title":
			return cluster.title;
		case "summary_rows.0":
			return cluster.summary_rows[0] ?? "";
		case "contrast_notes.0":
			return cluster.contrast_notes[0] ?? "";
	}
}

export function applyVocabularyClusterFieldEdit(
	cluster: SemanticAnchorCluster,
	field: EditableClusterField,
	nextValue: string,
): SemanticAnchorCluster {
	const trimmedValue = nextValue.trim();
	const nextCluster = (() => {
		switch (field) {
			case "title":
				return { ...cluster, title: trimmedValue };
			case "summary_rows.0":
				return { ...cluster, summary_rows: [trimmedValue, ...cluster.summary_rows.slice(1)] };
			case "contrast_notes.0":
				return { ...cluster, contrast_notes: [trimmedValue, ...cluster.contrast_notes.slice(1)] };
		}
	})();
	return SemanticAnchorClusterSchema.parse(nextCluster);
}

export function buildVocabularyPreferenceEvent(
	cluster: SemanticAnchorCluster,
	field: EditableClusterField,
	nextValue: string,
): VocabularyPreferenceEvent | null {
	const previousValue = fieldValue(cluster, field);
	const trimmedValue = nextValue.trim();
	if (previousValue === trimmedValue) return null;
	return {
		clusterId: cluster.cluster_id,
		fieldPath: field,
		previousValue,
		nextValue: trimmedValue,
	};
}

export function VocabularyBatchReviewEditor({ clusters, practiceSets, onDecisionAction }: VocabularyBatchReviewEditorProps) {
	const [selectedClusterId, setSelectedClusterId] = useState(clusters[0]?.cluster_id ?? "");
	const selectedCluster = clusters.find((cluster) => cluster.cluster_id === selectedClusterId) ?? clusters[0];
	const [draftTitle, setDraftTitle] = useState(selectedCluster?.title ?? "");
	const [draftSummary, setDraftSummary] = useState(selectedCluster?.summary_rows[0] ?? "");
	const [draftContrast, setDraftContrast] = useState(selectedCluster?.contrast_notes[0] ?? "");

	const validatedDraft = useMemo((): SemanticAnchorCluster | null => {
		if (!selectedCluster) return null;
		const edited = {
			...selectedCluster,
			title: draftTitle.trim(),
			summary_rows: [draftSummary.trim(), ...selectedCluster.summary_rows.slice(1)],
			contrast_notes: [draftContrast.trim(), ...selectedCluster.contrast_notes.slice(1)],
		};
		const validation = SemanticAnchorClusterSchema.safeParse(edited);
		return validation.success ? validation.data : null;
	}, [selectedCluster, draftTitle, draftSummary, draftContrast]);

	if (!selectedCluster) {
		return <p className="rounded-lg border bg-card p-6 text-sm text-muted-foreground">No vocabulary clusters are ready for review.</p>;
	}

	function selectCluster(cluster: SemanticAnchorCluster): void {
		setSelectedClusterId(cluster.cluster_id);
		setDraftTitle(cluster.title);
		setDraftSummary(cluster.summary_rows[0] ?? "");
		setDraftContrast(cluster.contrast_notes[0] ?? "");
	}

	function submit(action: VocabularyReviewAction): void {
		if (!validatedDraft) return;
		const preferenceEvents = [
			buildVocabularyPreferenceEvent(selectedCluster, "title", draftTitle),
			buildVocabularyPreferenceEvent(selectedCluster, "summary_rows.0", draftSummary),
			buildVocabularyPreferenceEvent(selectedCluster, "contrast_notes.0", draftContrast),
		].filter((event): event is VocabularyPreferenceEvent => event !== null);
		onDecisionAction?.({
			action,
			cluster: validatedDraft,
			preferenceEvents,
			unlockStudentExport: action === "approve" && selectedCluster.review_status === "needs_review",
		});
	}

	const studentExportWithheld = selectedCluster.review_status === "needs_review";

	return (
		<section aria-labelledby="vocabulary-review-title" className="grid gap-4 rounded-lg border bg-card p-6 text-card-foreground lg:grid-cols-[280px_1fr]">
			<div className="lg:col-span-2">
				<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Vocabulary batch review</p>
				<h3 id="vocabulary-review-title" className="text-lg font-semibold">Structured cluster editor</h3>
				<p className="text-sm text-muted-foreground">Edit validated contract fields, re-render previews, then approve, regenerate, or skip.</p>
			</div>
			<nav aria-label="Vocabulary clusters" className="space-y-2 rounded-lg border bg-background p-3">
				{clusters.map((cluster) => (
					<button
						key={cluster.cluster_id}
						type="button"
						onClick={() => selectCluster(cluster)}
						className="w-full rounded-md border bg-muted/40 p-3 text-left text-sm"
					>
						<span className="block font-medium">{cluster.title}</span>
						<span className="text-muted-foreground">{cluster.review_status} · {practiceCount(practiceSets, cluster.cluster_id)} practice items</span>
					</button>
				))}
			</nav>
			<div className="grid gap-4 xl:grid-cols-2">
				<div className="space-y-4 rounded-lg border bg-background p-4">
					<h4 className="text-sm font-semibold">Editable contract fields</h4>
					<label className="block text-sm font-medium">
						Cluster title
						<input className="mt-1 w-full rounded-md border bg-card p-2" value={draftTitle} onChange={(event) => setDraftTitle(event.target.value)} />
					</label>
					<label className="block text-sm font-medium">
						Summary row
						<textarea className="mt-1 w-full rounded-md border bg-card p-2" value={draftSummary} onChange={(event) => setDraftSummary(event.target.value)} />
					</label>
					<label className="block text-sm font-medium">
						Contrast note
						<textarea className="mt-1 w-full rounded-md border bg-card p-2" value={draftContrast} onChange={(event) => setDraftContrast(event.target.value)} />
					</label>
					{validatedDraft ? <p className="text-sm text-muted-foreground">Contract fields are valid and ready to re-render.</p> : <p className="text-sm font-medium text-destructive">Fix required fields before exporting.</p>}
					<div className="flex flex-wrap gap-2">
						<button type="button" disabled={!validatedDraft} onClick={() => submit("approve")} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground">Approve cluster</button>
						<button type="button" onClick={() => submit("regenerate")} className="rounded-md border px-3 py-2 text-sm font-semibold">Regenerate</button>
						<button type="button" onClick={() => submit("skip")} className="rounded-md border px-3 py-2 text-sm font-semibold">Skip</button>
					</div>
				</div>
				<div className="space-y-4 rounded-lg border bg-background p-4">
					<h4 className="text-sm font-semibold">Preview panes</h4>
					{studentExportWithheld ? <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">Student export withheld until a teacher approves this needs_review cluster.</div> : null}
					<div className="rounded-md border bg-card p-3">
						<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Teacher teaching preview</p>
						<h5 className="font-semibold">{draftTitle}</h5>
						<p className="text-sm text-muted-foreground">{draftSummary}</p>
						{selectedCluster.warnings.length > 0 ? <p className="mt-2 text-xs text-amber-700">{selectedCluster.warnings.join(" · ")}</p> : null}
					</div>
					<div className="rounded-md border bg-card p-3">
						<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Student-safe preview</p>
						<p className="text-sm">{selectedCluster.anchors[0]?.student_explanation_vi}</p>
						<p className="mt-2 text-xs text-muted-foreground">Teacher scripts, source notes, answers, and rationales are hidden here.</p>
					</div>
				</div>
			</div>
		</section>
	);
}
