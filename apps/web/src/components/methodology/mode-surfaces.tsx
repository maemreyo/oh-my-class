"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { MethodologyDetailPanels, type MethodologyInspectorDetails } from "./detail-panels";
import { METHODOLOGY_MODES, combinedPreviewMetadata, conflictRationale, modeByTag, type MethodologyTag } from "./mode-registry";

export interface MethodologyRequirementStatus {
	tag: string;
	component: string;
	status: "pass" | "warning" | "fail";
	jumpHref?: string;
}

export interface MethodologyWarning {
	severity: "info" | "warning" | "critical";
	message: string;
	jumpHref?: string;
}

export type { MethodologyInspectorDetails } from "./detail-panels";

export function MethodologyModePicker({
	selectedTag,
	disabledTags = [],
	selectedTags,
	onSelect,
}: {
	selectedTag: MethodologyTag;
	selectedTags?: readonly string[];
	disabledTags?: readonly string[];
	onSelect?: (tag: MethodologyTag) => void;
}) {
	const activeTags = selectedTags ?? [selectedTag];
	const previewMetadata = combinedPreviewMetadata(activeTags);
	return (
		<section aria-label="Methodology mode picker" className="space-y-3">
			{previewMetadata ? <p className="rounded-md border border-border bg-muted p-3 text-sm text-muted-foreground">{previewMetadata}</p> : null}
			<div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
				{METHODOLOGY_MODES.map((mode) => {
					const conflict = activeTags.map((tag) => conflictRationale(tag, mode.tag)).find((rationale) => rationale !== null);
					const disabled = disabledTags.includes(mode.tag) || Boolean(conflict);
					const selected = activeTags.includes(mode.tag);
					return (
						<button
							key={mode.tag}
							type="button"
							disabled={disabled}
							aria-pressed={selected}
							onClick={() => onSelect?.(mode.tag)}
							className="rounded-lg border border-border bg-card p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 data-[selected=true]:border-primary data-[selected=true]:bg-primary/10"
							data-selected={selected}
						>
							<span className="block text-sm font-semibold">{mode.label}</span>
							<span className="mt-1 block text-sm text-muted-foreground">{mode.description}</span>
							{conflict ? <span className="mt-2 block text-xs text-destructive">{conflict}</span> : null}
						</button>
					);
				})}
			</div>
		</section>
	);
}

export function MethodologyInspectorPanel({
	declaredTags,
	requirements,
	warnings = [],
	details,
}: {
	declaredTags: readonly string[];
	requirements: readonly MethodologyRequirementStatus[];
	warnings?: readonly MethodologyWarning[];
	details?: MethodologyInspectorDetails;
}) {
	return (
		<aside aria-label="Methodology inspector" className="rounded-lg border border-border bg-card p-4">
			<h3 className="text-lg font-semibold">Methodology inspector</h3>
			<div className="mt-3 flex flex-wrap gap-2">
				{declaredTags.map((tag) => <span key={tag} className="rounded-full border border-border px-3 py-1 text-sm">{modeByTag(tag)?.label ?? tag}</span>)}
			</div>
			<MethodologyDetailPanels declaredTags={declaredTags} details={details} />
			<div className="mt-4 grid gap-3 md:grid-cols-3">
				<StatusGroup title="Pass" statuses={requirements.filter((item) => item.status === "pass")} />
				<StatusGroup title="Warning" statuses={requirements.filter((item) => item.status === "warning")} warnings={warnings} />
				<StatusGroup title="Fail" statuses={requirements.filter((item) => item.status === "fail")} />
			</div>
		</aside>
	);
}

function StatusGroup({ title, statuses, warnings = [] }: { title: string; statuses: readonly MethodologyRequirementStatus[]; warnings?: readonly MethodologyWarning[] }) {
	return (
		<section className="rounded-md border border-border bg-background p-3" aria-label={title}>
			<h4 className="font-medium">{title}</h4>
			<ul className="mt-2 space-y-1 text-sm">
				{statuses.map((item) => <li key={`${item.tag}-${item.component}`}><a href={item.jumpHref ?? "#"}>{item.tag}: {item.component}</a></li>)}
				{warnings.map((warning) => <li key={warning.message} role="alert"><a href={warning.jumpHref ?? "#"}>{warning.severity}: {warning.message}</a></li>)}
			</ul>
		</section>
	);
}

export function MethodologyPreviewShell({ html, width = "desktop" }: { html: string; width?: "desktop" | "tablet" | "mobile" }) {
	const maxWidth = width === "mobile" ? "max-w-sm" : width === "tablet" ? "max-w-3xl" : "max-w-6xl";
	return (
		<section className="rounded-lg border border-border bg-card p-4" aria-label="Methodology preview">
			<div className="flex flex-wrap gap-2">
				<Button type="button" variant={width === "desktop" ? "secondary" : "outline"}>Desktop</Button>
				<Button type="button" variant={width === "tablet" ? "secondary" : "outline"}>Tablet</Button>
				<Button type="button" variant={width === "mobile" ? "secondary" : "outline"}>Mobile</Button>
			</div>
			<div className={`mx-auto mt-4 ${maxWidth}`}>
				<iframe title="Methodology preview" srcDoc={html} sandbox="allow-same-origin" className="h-96 w-full rounded-md border border-border" />
			</div>
		</section>
	);
}
