"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export interface ArtifactRejection {
	readonly artifact_id: string;
	readonly reason: string;
}

export interface ArtifactSectionTarget {
	readonly section_id: string;
	readonly title: string;
	readonly content: string;
}

export interface EditableArtifactTarget {
	readonly id: string;
	readonly type: string;
	readonly sections?: readonly ArtifactSectionTarget[];
}

export interface ContentSectionEdit {
	readonly artifact_id: string;
	readonly section_id: string;
	readonly component_id?: string;
	readonly replacement_content: string;
	readonly rationale: string;
}

export interface TeachingPackScopedRejectionProps {
	readonly artifacts: readonly EditableArtifactTarget[];
	readonly onReject: (rejections: readonly ArtifactRejection[]) => Promise<void> | void;
	readonly disabled?: boolean;
}

export interface TeachingPackSectionEditorProps {
	readonly artifacts: readonly EditableArtifactTarget[];
	readonly onSubmit: (edit: ContentSectionEdit) => Promise<void> | void;
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

export function TeachingPackSectionEditor({
	artifacts,
	onSubmit,
	disabled,
}: TeachingPackSectionEditorProps) {
	const [draft, setDraft] = useState<ContentSectionEdit>(() => initialSectionEdit(artifacts));
	const [isSubmitting, setIsSubmitting] = useState(false);
	const selectedArtifact = artifacts.find((artifact) => artifact.id === draft.artifact_id);
	const sections = selectedArtifact?.sections ?? [];
	const canSubmit = draft.artifact_id.length > 0 && draft.section_id.length > 0 && draft.replacement_content.trim().length > 0 && !disabled && !isSubmitting;

	const selectArtifact = (artifactId: string) => {
		const artifact = artifacts.find((item) => item.id === artifactId);
		const firstSection = artifact?.sections?.[0];
		setDraft({
			artifact_id: artifactId,
			section_id: firstSection?.section_id ?? "",
			replacement_content: firstSection?.content ?? "",
			rationale: draft.rationale,
		});
	};

	const selectSection = (sectionId: string) => {
		const section = sections.find((item) => item.section_id === sectionId);
		setDraft({
			...draft,
			section_id: sectionId,
			replacement_content: section?.content ?? draft.replacement_content,
		});
	};

	const submit = async () => {
		setIsSubmitting(true);
		try {
			await onSubmit(createSectionEditPayload(draft));
		} finally {
			setIsSubmitting(false);
		}
	};

	if (artifacts.length === 0) {
		return <p className="text-sm text-muted-foreground">No editable artifacts are available.</p>;
	}

	return (
		<div className="space-y-4">
			<div>
				<p className="text-sm font-medium">Structured section editor</p>
				<p className="mt-1 text-sm text-muted-foreground">Create a versioned content edit for one section or component.</p>
			</div>

			<div className="grid gap-3 md:grid-cols-2">
				<label className="space-y-2">
					<span className="text-sm font-medium">Artifact</span>
					<select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={draft.artifact_id} onChange={(event) => selectArtifact(event.currentTarget.value)} disabled={disabled || isSubmitting}>
						{artifacts.map((artifact) => <option key={artifact.id} value={artifact.id}>{artifact.type}</option>)}
					</select>
				</label>
				<label className="space-y-2">
					<span className="text-sm font-medium">Section</span>
					<select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={draft.section_id} onChange={(event) => selectSection(event.currentTarget.value)} disabled={disabled || isSubmitting || sections.length === 0}>
						{sections.map((section) => <option key={section.section_id} value={section.section_id}>{section.title}</option>)}
					</select>
				</label>
			</div>

			<label className="space-y-2">
				<span className="text-sm font-medium">Replacement content</span>
				<textarea className="min-h-32 w-full rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50" value={draft.replacement_content} onChange={(event) => setDraft({ ...draft, replacement_content: event.currentTarget.value })} disabled={disabled || isSubmitting} />
			</label>

			<label className="space-y-2">
				<span className="text-sm font-medium">Teacher rationale</span>
				<textarea className="min-h-20 w-full rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50" value={draft.rationale} onChange={(event) => setDraft({ ...draft, rationale: event.currentTarget.value })} disabled={disabled || isSubmitting} placeholder="Why should this section change?" />
			</label>

			<Button type="button" variant="secondary" onClick={submit} disabled={!canSubmit}>
				{isSubmitting ? "Submitting..." : "Submit section edit"}
			</Button>
		</div>
	);
}

export function initialSectionEdit(artifacts: readonly EditableArtifactTarget[]): ContentSectionEdit {
	const artifact = artifacts[0];
	const section = artifact?.sections?.[0];
	return {
		artifact_id: artifact?.id ?? "",
		section_id: section?.section_id ?? "",
		replacement_content: section?.content ?? "",
		rationale: "",
	};
}

export function createSectionEditPayload(edit: ContentSectionEdit): ContentSectionEdit {
	return {
		artifact_id: edit.artifact_id,
		section_id: edit.section_id,
		component_id: edit.component_id,
		replacement_content: edit.replacement_content,
		rationale: edit.rationale.trim(),
	};
}
