"use client";

import { useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Check, LoaderCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAutosaveTeachingBrief, useCreateTeachingBrief, useLaunchTeachingBrief } from "@/hooks/use-teaching-brief";
import type { TeachingBrief, TeachingBriefArtifactType, TeachingBriefExportFormat } from "@/types/teaching-pack-api";

const CORE_ARTIFACTS: readonly { readonly value: TeachingBriefArtifactType; readonly label: string; readonly detail: string }[] = [
	{ value: "lesson", label: "Lesson", detail: "Teacher flow and instruction." },
	{ value: "worksheet", label: "Worksheet", detail: "Student practice." },
	{ value: "quiz", label: "Quiz", detail: "Check for understanding." },
	{ value: "recap", label: "Recap", detail: "End-of-class review." },
	{ value: "slide_deck", label: "Slides", detail: "Presentable teaching deck." },
];
const EXPORTS: readonly TeachingBriefExportFormat[] = ["html", "gift", "h5p", "pptx"];
const RESEARCH_POLICIES = ["basic", "standard", "rigorous"] as const;

const INITIAL_BRIEF: TeachingBrief = {
	raw_request: "",
	topic: "",
	grade: 5,
	subject: "",
	target_language: "en",
	instruction_language: "en",
	curriculum: null,
	class_context: "",
	artifact_types: CORE_ARTIFACTS.map((artifact) => artifact.value),
	export_formats: ["html"],
	methodology: null,
	research_policy: "standard",
	must_include: "",
	avoid: "",
	always_review: false,
};

export default function NewRunPage() {
	const router = useRouter();
	const [brief, setBrief] = useState<TeachingBrief>(INITIAL_BRIEF);
	const [briefId, setBriefId] = useState<string | null>(null);
	const createMutation = useCreateTeachingBrief();
	const autosaveMutation = useAutosaveTeachingBrief(briefId);
	const launchMutation = useLaunchTeachingBrief(briefId);
	const createBriefRef = useRef(createMutation.mutate);
	const autosaveBriefRef = useRef(autosaveMutation.mutate);
	createBriefRef.current = createMutation.mutate;
	autosaveBriefRef.current = autosaveMutation.mutate;
	const launchBrief = launchMutation.mutateAsync;
	const materiality = useMemo(() => materialityReasons(brief), [brief]);
	const isComplete = brief.raw_request.trim() !== "" && brief.topic.trim() !== "" && brief.subject.trim() !== "";

	const saveState = createMutation.isPending || autosaveMutation.isPending ? "Saving draft" : briefId ? "Saved to workspace" : "Complete the required fields to save";
	const saveError = createMutation.error ?? autosaveMutation.error ?? launchMutation.error;

	async function launch(): Promise<void> {
		if (!briefId) return;
		const result = await launchBrief();
		router.push(`/runs/${result.run_id}`);
	}

	function updateBrief(nextBrief: TeachingBrief): void {
		setBrief(nextBrief);
		if (nextBrief.raw_request.trim() === "" || nextBrief.topic.trim() === "" || nextBrief.subject.trim() === "") return;
		if (briefId) {
			autosaveBriefRef.current(nextBrief);
		} else {
			createBriefRef.current(nextBrief, { onSuccess: (saved) => setBriefId(saved.brief_id) });
		}
	}

	return (
		<main className="mx-auto max-w-6xl space-y-6 p-4 md:p-8" aria-labelledby="creator-title">
			<header className="space-y-2">
				<p className="text-sm font-medium text-muted-foreground">Creator Workspace</p>
				<h1 id="creator-title" className="text-3xl font-bold tracking-tight">Build a teaching pack</h1>
				<p className="max-w-3xl text-muted-foreground">Describe the lesson once. The workspace preserves your brief, shows the resolved scope, and asks for review only when a material choice needs it.</p>
			</header>

			{saveError && <p role="alert" className="rounded-md border border-destructive p-3 text-sm text-destructive">{saveError.message}</p>}
			<section aria-labelledby="brief-heading" className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
				<Card>
					<CardHeader><CardTitle id="brief-heading" className="text-lg">Teaching Brief</CardTitle></CardHeader>
					<CardContent className="space-y-4">
						<Field label="What should students learn?" required><textarea id="raw-request" value={brief.raw_request} onChange={(event) => updateBrief({ ...brief, raw_request: event.currentTarget.value })} className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" placeholder="Teach Grade 5 students how to compare equivalent fractions through visual models." /></Field>
						<div className="grid gap-4 sm:grid-cols-2"><Field label="Topic" required><Input value={brief.topic} onChange={(event) => updateBrief({ ...brief, topic: event.currentTarget.value })} /></Field><Field label="Subject" required><Input value={brief.subject} onChange={(event) => updateBrief({ ...brief, subject: event.currentTarget.value })} /></Field></div>
						<div className="grid gap-4 sm:grid-cols-3"><Field label="Grade"><select id="grade" value={brief.grade} onChange={(event) => updateBrief({ ...brief, grade: Number(event.currentTarget.value) })} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{Array.from({ length: 12 }, (_, index) => index + 1).map((grade) => <option key={grade} value={grade}>Grade {grade}</option>)}</select></Field><Field label="Target language"><LanguageSelect value={brief.target_language} onChange={(target_language) => updateBrief({ ...brief, target_language })} /></Field><Field label="Instruction language"><LanguageSelect value={brief.instruction_language} onChange={(instruction_language) => updateBrief({ ...brief, instruction_language })} /></Field></div>
						<Field label="Class context"><Input value={brief.class_context} onChange={(event) => updateBrief({ ...brief, class_context: event.currentTarget.value })} placeholder="30 students; mixed confidence with fraction models" /></Field>
						<Field label="Must include"><Input value={brief.must_include} onChange={(event) => updateBrief({ ...brief, must_include: event.currentTarget.value })} placeholder="Visual fraction bars and one exit check" /></Field>
						<Field label="Avoid"><Input value={brief.avoid} onChange={(event) => updateBrief({ ...brief, avoid: event.currentTarget.value })} placeholder="Long word problems" /></Field>
					</CardContent>
				</Card>
				<aside className="space-y-4" aria-label="Brief save status and planning review">
					<Card><CardHeader><CardTitle className="text-lg">Workspace status</CardTitle></CardHeader><CardContent className="space-y-3 text-sm"><p aria-live="polite" className="flex items-center gap-2"><Check className="size-4 text-primary" aria-hidden="true" />{saveState}</p><p className="text-muted-foreground">Drafts are stored on the server before you launch a pack.</p></CardContent></Card>
					<Card><CardHeader><CardTitle className="text-lg">Planning Review</CardTitle></CardHeader><CardContent className="space-y-3 text-sm">{materiality.length === 0 ? <p className="text-muted-foreground">No material changes. The plan can proceed after the standard contract check.</p> : <><p className="flex items-center gap-2 font-medium"><AlertCircle className="size-4 text-primary" aria-hidden="true" />Review required</p><ul className="list-disc space-y-1 pl-5 text-muted-foreground">{materiality.map((reason) => <li key={reason}>{reason}</li>)}</ul></>}</CardContent></Card>
				</aside>
			</section>

			<section aria-labelledby="scope-heading" className="grid gap-6 lg:grid-cols-2"><Card><CardHeader><CardTitle id="scope-heading" className="text-lg">Pack recipe</CardTitle></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2">{CORE_ARTIFACTS.map((artifact) => <label key={artifact.value} className="rounded-md border border-border bg-background p-3"><input type="checkbox" checked={brief.artifact_types.includes(artifact.value)} onChange={() => updateBrief({ ...brief, artifact_types: toggle(brief.artifact_types, artifact.value) })} className="mr-2" /><span className="text-sm font-medium">{artifact.label}</span><p className="mt-1 text-xs text-muted-foreground">{artifact.detail}</p></label>)}</CardContent></Card><Card><CardHeader><CardTitle className="text-lg">Research and output</CardTitle></CardHeader><CardContent className="space-y-4"><Field label="Research rigor"><select value={brief.research_policy} onChange={(event) => updateBrief({ ...brief, research_policy: researchPolicy(event.currentTarget.value) })} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{RESEARCH_POLICIES.map((policy) => <option key={policy} value={policy}>{policy[0].toUpperCase()}{policy.slice(1)}</option>)}</select></Field><fieldset><legend className="text-sm font-medium">Export formats</legend><div className="mt-2 flex flex-wrap gap-3">{EXPORTS.map((format) => <label key={format} className="text-sm"><input type="checkbox" checked={brief.export_formats.includes(format)} onChange={() => updateBrief({ ...brief, export_formats: toggle(brief.export_formats, format) })} className="mr-2" />{format.toUpperCase()}</label>)}</div></fieldset><label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={brief.always_review} onChange={(event) => updateBrief({ ...brief, always_review: event.currentTarget.checked })} className="mt-1" />Always review the plan before generation</label></CardContent></Card></section>
			<div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-muted-foreground">Final content still needs teacher approval after generation.</p><Button type="button" size="lg" disabled={!briefId || launchMutation.isPending} onClick={() => void launch()}>{launchMutation.isPending ? <LoaderCircle className="mr-2 size-4 animate-spin" aria-hidden="true" /> : <Sparkles className="mr-2 size-4" aria-hidden="true" />}{materiality.length > 0 ? "Review plan and generate" : "Generate teaching pack"}</Button></div>
		</main>
	);
}

function Field({ label, required = false, children }: { readonly label: string; readonly required?: boolean; readonly children: React.ReactNode }) { return <label className="block space-y-2"><span className="text-sm font-medium">{label}{required && <span aria-hidden="true"> *</span>}</span>{children}</label>; }
function LanguageSelect({ value, onChange }: { readonly value: string; readonly onChange: (value: string) => void }) { return <select value={value} onChange={(event) => onChange(event.currentTarget.value)} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><option value="en">English</option><option value="vi">Vietnamese</option></select>; }
function toggle<T>(values: readonly T[], value: T): T[] { return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]; }
function researchPolicy(value: string): TeachingBrief["research_policy"] { switch (value) { case "basic": return "basic"; case "rigorous": return "rigorous"; default: return "standard"; } }
function materialityReasons(brief: TeachingBrief): string[] { const reasons: string[] = []; if (brief.always_review) reasons.push("You chose always review"); if (brief.research_policy === "rigorous") reasons.push("Rigorous research"); if (brief.export_formats.some((format) => format !== "html")) reasons.push("Additional export format"); if (brief.artifact_types.length !== CORE_ARTIFACTS.length) reasons.push("Custom artifact scope"); return reasons; }
