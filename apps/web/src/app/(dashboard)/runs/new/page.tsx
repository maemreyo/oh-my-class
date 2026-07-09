"use client";

import { InverseThinkingEditor } from "@/components/inverse-thinking-editor";
import { MethodologyInspectorPanel, MethodologyModePicker, MethodologyPreviewShell } from "@/components/methodology/mode-surfaces";
import { TEMPLATE_REFERENCE_MODES, renderTemplateReferencePreview } from "@/components/methodology/template-reference-modes";
import { StructurePresetPicker } from "@/components/slide-deck/structure-preset-picker";
import { ExportFormatChooser, StandardGatePreview, StandardPackPreviewShell } from "@/components/standard-pack/standard-pack-baseline";

const previewHtml = `<!DOCTYPE html><html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>body{font-family:system-ui;padding:24px}article{border:1px solid currentColor;border-radius:16px;padding:16px}@media print{body{padding:0}}</style></head><body><article><p>oh-my-class</p><h1>Student preview</h1><p>A student writes: I have visited Da Nang yesterday.</p></article></body></html>`;
const templateReferencePreviewHtml = renderTemplateReferencePreview(TEMPLATE_REFERENCE_MODES[0]);

export default function NewRunPage() {
	return (
		<div className="mx-auto max-w-6xl space-y-6 p-4 md:p-8">
			<div>
				<p className="text-sm font-medium text-muted-foreground">Create teaching pack</p>
				<h1 className="mt-1 text-3xl font-bold tracking-tight">Teaching approach</h1>
				<p className="mt-2 max-w-3xl text-muted-foreground">
					Choose a standard pack or open the structured inverse-thinking editor for disaster-first lessons.
				</p>
			</div>
			<StandardGatePreview gate="content_approval" state="export_ready" completeness={92} qualityStatus="pass" exportReady />
			<StructurePresetPicker selectedPresetId={null} />
			<StandardPackPreviewShell artifact="lesson" theme="default" html={previewHtml} viewport="desktop" />
			<ExportFormatChooser selectedArtifacts={["lesson", "quiz"]} selectedFormats={["html"]} />
				<MethodologyModePicker selectedTag="inverse_thinking" disabledTags={TEMPLATE_REFERENCE_MODES.map((mode) => mode.tag)} />
				<section className="rounded-lg border border-border bg-card p-4" aria-label="Template reference modes">
					<h3 className="text-lg font-semibold">Template reference modes</h3>
					<p className="mt-1 text-sm text-muted-foreground">Raw reference templates are inventoried as offline-safe design contracts before full methodology implementation.</p>
					<div className="mt-3 grid gap-2 md:grid-cols-2">
						{TEMPLATE_REFERENCE_MODES.map((mode) => (
							<div key={mode.tag} className="rounded-md border border-border bg-background p-3 text-sm">
								<p className="font-medium">{mode.label}</p>
								<p className="mt-1 text-muted-foreground">{mode.sourceTemplate}</p>
								<p className="mt-2 text-muted-foreground">{mode.followUp}</p>
							</div>
						))}
					</div>
				</section>
			<MethodologyInspectorPanel
				declaredTags={["concept_map"]}
				requirements={[{ tag: "concept_map", component: "vocab_cluster or contrastive_pairs", status: "fail", jumpHref: "#concept-map" }]}
			/>
			<MethodologyInspectorPanel
				declaredTags={["contrastive_pairs"]}
				requirements={[{ tag: "contrastive_pairs", component: "contrastive_pairs", status: "pass", jumpHref: "#contrastive-pairs" }]}
				details={{
					contrastivePair: {
						title: "Because vs Although",
						leftLabel: "Because: gives the reason",
						rightLabel: "Although: shows contrast",
						reason: "Students often confuse expected cause with surprising contrast, so the pair needs shared criteria and explicit difference markers.",
					},
				}}
			/>
			<MethodologyInspectorPanel
				declaredTags={["film_based"]}
				requirements={[{ tag: "film_based", component: "film_clip_activity", status: "pass", jumpHref: "#film-based" }]}
				details={{
					filmActivity: {
						title: "Bus stop scene",
						context: "Teacher-provided clip context is recorded as text so standalone exports remain offline-safe.",
						before: "Predict which connector introduces the reason.",
						during: "Listen for because, although, and the clause after each connector.",
						after: "Explain which connector matched the speaker's purpose.",
					},
				}}
			/>
			<MethodologyInspectorPanel
				declaredTags={["shy_student_1on1"]}
				requirements={[{ tag: "shy_student_1on1", component: "roleplay_script", status: "pass", jumpHref: "#roleplay" }]}
				details={{
					shyStudent: {
						intent: "Low-pressure private rehearsal before any sharing, with quiet choices and supportive prompts.",
						requiredComponent: "roleplay_script",
						coachingNotesSeparated: true,
					},
				}}
			/>
				<MethodologyInspectorPanel
					declaredTags={["active_recall"]}
					requirements={[{ tag: "active_recall", component: "active_recall_prompt", status: "pass", jumpHref: "#recall" }]}
				details={{
					activeRecall: {
						intent: "Students retrieve from memory before seeing support, then check confidence and reflect.",
						requiredComponent: "active_recall_prompt",
						revealSeparated: true,
					},
					}}
				/>
				<MethodologyInspectorPanel
					declaredTags={["why_wrong_reasoning"]}
					requirements={[{ tag: "why_wrong_reasoning", component: "wrong_reasons", status: "warning", jumpHref: "#question-card-q2-wrong-reasons" }]}
					details={{
						whyWrongReasoning: {
							questions: [{
								id: "q2",
								prompt: "Which connector fits the contrast?",
								options: { A: "because", B: "although", C: "and" },
								answer: "B",
								wrongReasons: { A: "A gives a cause, not a contrast." },
							}],
						},
					}}
				/>
				<MethodologyInspectorPanel
					declaredTags={["timed_quiz"]}
					requirements={[{ tag: "timed_quiz", component: "time_limit", status: "warning", jumpHref: "#timed-quiz-duration" }]}
					details={{ timedQuiz: { settings: { durationMinutes: 8, intensity: "balanced" }, timedItemCount: 2, totalItemCount: 3 } }}
				/>
				<InverseThinkingEditor renderedHtml={previewHtml} />
				<MethodologyPreviewShell html={templateReferencePreviewHtml} width="desktop" />
			</div>
		);
}
