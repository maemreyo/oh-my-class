"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";

export type StandardArtifactType = "lesson" | "worksheet" | "quiz" | "drill" | "recap" | "infographic";
export type StandardTheme = "default" | "ocean" | "forest";
export type PreviewViewport = "desktop" | "tablet" | "mobile" | "print";
export type GatePreviewState =
	| "empty"
	| "loading"
	| "quality_failed"
	| "repair_in_progress"
	| "teacher_rejected"
	| "export_ready";
export type GateName = "blueprint_approval" | "content_approval";
export type QualityStatus = "pending" | "pass" | "fail";
export type ExportFormat = "html" | "gift" | "h5p" | "qti";

export interface StandardArtifactOption {
	readonly type: StandardArtifactType;
	readonly label: string;
	readonly description: string;
}

export interface ExportFormatStatus {
	readonly enabled: boolean;
	readonly explanation: string;
}

export type ExportAvailability = Readonly<Record<ExportFormat, ExportFormatStatus>>;

export const STANDARD_ARTIFACTS: readonly StandardArtifactOption[] = [
	{ type: "lesson", label: "Lesson", description: "Teacher flow, objectives, and guided instruction." },
	{ type: "worksheet", label: "Worksheet", description: "Printable student practice with open response space." },
	{ type: "quiz", label: "Quiz", description: "Check-for-understanding questions with teacher-only answers." },
	{ type: "drill", label: "Drill", description: "Short repetition set for fluency and retrieval." },
	{ type: "recap", label: "Recap", description: "Compact review notes for the end of class." },
	{ type: "infographic", label: "Infographic", description: "Visual summary for classroom display or handout." },
];

const themeLabels: Readonly<Record<StandardTheme, string>> = {
	default: "Default theme",
	ocean: "Ocean theme",
	forest: "Forest theme",
};

const viewportClasses: Readonly<Record<PreviewViewport, string>> = {
	desktop: "max-w-6xl",
	tablet: "max-w-3xl",
	mobile: "max-w-sm",
	print: "max-w-4xl bg-background",
};

const gateStateCopy: Readonly<Record<GatePreviewState, { readonly primary: string; readonly secondary: string; readonly copy: string }>> = {
	empty: { primary: "Start blueprint", secondary: "Add lesson details", copy: "No standard pack content yet." },
	loading: { primary: "Generating", secondary: "View run log", copy: "Building the standard pack preview." },
	quality_failed: { primary: "Repair pack", secondary: "Open quality report", copy: "Quality gates found blocking issues." },
	repair_in_progress: { primary: "Repairing", secondary: "View repair plan", copy: "Repair is in progress." },
	teacher_rejected: { primary: "Revise content", secondary: "Review feedback", copy: "Teacher feedback requires changes." },
	export_ready: { primary: "Export pack", secondary: "Preview all artifacts", copy: "Ready for export." },
};

export function artifactLabel(type: StandardArtifactType): string {
	return STANDARD_ARTIFACTS.find((artifact) => artifact.type === type)?.label ?? type;
}

export function exportFormatAvailability(selectedArtifacts: readonly StandardArtifactType[]): ExportAvailability {
	const selected = new Set(selectedArtifacts);
	const hasLesson = selected.has("lesson");
	const hasQuiz = selected.has("quiz");
	return {
		html: { enabled: hasLesson, explanation: hasLesson ? "HTML export is ready." : "HTML export needs a lesson artifact." },
		gift: { enabled: hasQuiz, explanation: hasQuiz ? "GIFT export is ready." : "GIFT export needs a quiz artifact." },
		h5p: { enabled: hasQuiz, explanation: hasQuiz ? "H5P export is ready." : "H5P export needs a quiz artifact." },
		qti: { enabled: hasQuiz, explanation: hasQuiz ? "QTI export is ready." : "QTI export needs a quiz artifact." },
	};
}

export function StandardPackPreviewShell({
	artifact,
	theme,
	html,
	viewport,
}: {
	readonly artifact: StandardArtifactType;
	readonly theme: StandardTheme;
	readonly html: string;
	readonly viewport: PreviewViewport;
}) {
	return (
		<section aria-label="Standard pack preview" className="rounded-lg border border-border bg-card p-4">
			<div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
				<div>
					<p className="text-sm font-medium text-muted-foreground">Standard teaching pack</p>
					<h2 className="mt-1 text-2xl font-bold tracking-tight">{artifactLabel(artifact)}</h2>
					<p className="mt-1 text-sm text-muted-foreground">{themeLabels[theme]}</p>
				</div>
				<div role="tablist" aria-label="Preview viewport" className="flex flex-wrap gap-2">
					{(["desktop", "tablet", "mobile", "print"] as const).map((item) => (
						<Button key={item} type="button" variant={viewport === item ? "secondary" : "outline"} role="tab" aria-selected={viewport === item}>
							{labelViewport(item)}
						</Button>
					))}
				</div>
			</div>
			<div className="mt-4 grid gap-2 md:grid-cols-3 xl:grid-cols-6">
				{STANDARD_ARTIFACTS.map((item) => (
					<div key={item.type} className="rounded-md border border-border bg-background p-3">
						<p className="text-sm font-medium">{item.label}</p>
						<p className="mt-1 text-xs text-muted-foreground">{item.description}</p>
					</div>
				))}
			</div>
			<div className={`mx-auto mt-4 ${viewportClasses[viewport]}`}>
				<iframe title={`${artifactLabel(artifact)} preview`} srcDoc={html} sandbox="allow-same-origin" className="h-96 w-full rounded-md border border-border" />
			</div>
		</section>
	);
}

function labelViewport(viewport: PreviewViewport): string {
	const labels: Readonly<Record<PreviewViewport, string>> = { desktop: "Desktop", tablet: "Tablet", mobile: "Mobile", print: "Print" };
	return labels[viewport];
}

export function StandardGatePreview({
	gate,
	state,
	completeness,
	qualityStatus,
	exportReady,
}: {
	readonly gate: GateName;
	readonly state: GatePreviewState;
	readonly completeness: number;
	readonly qualityStatus: QualityStatus;
	readonly exportReady: boolean;
}) {
	const copy = gateStateCopy[state];
	return (
		<section aria-label="Teacher gate preview" className="rounded-lg border border-border bg-card p-4">
			<div aria-live="polite" className="grid gap-3 md:grid-cols-4">
				<GateMetric label="Gate" value={gate === "blueprint_approval" ? "Teacher Gate 1" : "Teacher Gate 2"} />
				<GateMetric label="Completeness" value={`${completeness}%`} />
				<GateMetric label="Quality" value={qualityStatus} />
				<GateMetric label="Export" value={exportReady ? "ready" : "blocked"} />
			</div>
			<p className="mt-4 text-sm text-muted-foreground">{copy.copy}</p>
			<div className="mt-4 flex flex-wrap gap-2">
				<Button type="button" disabled={state === "loading" || state === "repair_in_progress"}>{copy.primary}</Button>
				<Button type="button" variant="outline">{copy.secondary}</Button>
			</div>
		</section>
	);
}

function GateMetric({ label, value }: { readonly label: string; readonly value: string }) {
	return (
		<div className="rounded-md border border-border bg-background p-3">
			<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
			<p className="mt-1 text-sm font-medium">{value}</p>
		</div>
	);
}

export function ExportFormatChooser({
	selectedArtifacts,
	selectedFormats,
}: {
	readonly selectedArtifacts: readonly StandardArtifactType[];
	readonly selectedFormats: readonly ExportFormat[];
}) {
	const availability = exportFormatAvailability(selectedArtifacts);
	const formats = Object.entries(availability) as ReadonlyArray<[ExportFormat, ExportFormatStatus]>;
	return (
		<section aria-label="Export readiness" className="rounded-lg border border-border bg-card p-4">
			<h2 className="text-lg font-semibold">Export readiness</h2>
			<div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
				{formats.map(([format, status]) => {
					const descriptionId = `export-${format}-description`;
					return (
						<label key={format} className="rounded-md border border-border bg-background p-3">
							<input type="checkbox" className="mr-2" checked={selectedFormats.includes(format)} disabled={!status.enabled} readOnly aria-describedby={descriptionId} />
							<span className="text-sm font-medium uppercase">{format}</span>
							<p id={descriptionId} className="mt-1 text-xs text-muted-foreground">{status.explanation}</p>
						</label>
					);
				})}
			</div>
		</section>
	);
}
