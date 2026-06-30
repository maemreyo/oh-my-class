export type TemplateReferenceTag =
	| "key_reference"
	| "path_reference"
	| "learning_vocab_reference"
	| "learning_video_reference";

export interface TemplateReferenceMode {
	readonly tag: TemplateReferenceTag;
	readonly label: string;
	readonly sourceTemplate: string;
	readonly description: string;
	readonly reusablePrimitives: readonly string[];
	readonly teacherControls: readonly string[];
	readonly rendererSurfaces: readonly string[];
	readonly qualityExpectations: readonly string[];
	readonly followUp: string;
}

export const TEMPLATE_REFERENCE_MODES: readonly TemplateReferenceMode[] = [
	{
		tag: "key_reference",
		label: "Key Reference",
		sourceTemplate: "docs/templates/key-template.html",
		description: "Teacher-only answer-key layout with grouped explanations and misconception feedback.",
		reusablePrimitives: ["answer-key shell", "grouped question card", "wrong-reason feedback", "range navigation"],
		teacherControls: ["answer visibility", "range labels", "misconception emphasis", "print density"],
		rendererSurfaces: ["answer_key", "question_card", "wrong_reason_feedback"],
		qualityExpectations: ["teacher-only answers", "question anchors", "student answer leakage blocked"],
		followUp: "Implementation-ready through existing answer-key renderer polish.",
	},
	{
		tag: "path_reference",
		label: "Path Reference",
		sourceTemplate: "docs/templates/path-template.html",
		description: "Roadmap-style learning path with phases, checkpoints, and target progress cards.",
		reusablePrimitives: ["roadmap shell", "phase timeline", "goal card", "checkpoint checklist"],
		teacherControls: ["target level", "phase count", "checkpoint cadence", "remediation emphasis"],
		rendererSurfaces: ["roadmap", "phase_timeline", "stat_grid"],
		qualityExpectations: ["phase goal present", "checkpoint present", "print-safe progress text"],
		followUp: "Implementation-ready through roadmap renderer polish.",
	},
	{
		tag: "learning_vocab_reference",
		label: "Learning Vocab Reference",
		sourceTemplate: "docs/templates/learning-vocab-template.html",
		description: "Vocabulary lesson layout with concept clusters, contrast pairs, and homework carryover.",
		reusablePrimitives: ["vocab cluster", "concept triad", "contrast table", "homework list"],
		teacherControls: ["vocabulary set", "contrast emphasis", "video optionality", "homework density"],
		rendererSurfaces: ["lesson", "vocab_cluster", "contrastive_pairs", "hw_list"],
		qualityExpectations: ["definitions/examples present", "teacher rationale separated", "media text-only"],
		followUp: "Implementation-ready through existing methodology component polish.",
	},
	{
		tag: "learning_video_reference",
		label: "Learning via Video Reference",
		sourceTemplate: "docs/templates/learning-via-video-template.html",
		description: "Video-learning station path with before, during, after, and self-check tasks.",
		reusablePrimitives: ["ticket header", "station timeline", "viewing task card", "clue chips"],
		teacherControls: ["clip context", "station sequence", "viewing pass count", "reflection prompt"],
		rendererSurfaces: ["film_clip_activity", "phase_timeline", "reflection note"],
		qualityExpectations: ["no embedded video", "before/during/after prompts", "text-readable transcript clues"],
		followUp: "Implementation-ready through film-based renderer polish.",
	},
];

export function templateReferenceModeByTag(tag: string): TemplateReferenceMode | null {
	return TEMPLATE_REFERENCE_MODES.find((mode) => mode.tag === tag) ?? null;
}

export function renderTemplateReferencePreview(mode: TemplateReferenceMode): string {
	const primitives = mode.reusablePrimitives.map((primitive) => `<li>${primitive}</li>`).join("");
	const controls = mode.teacherControls.map((control) => `<li>${control}</li>`).join("");
	return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>${mode.label} — oh-my-class</title><style>:root{--surface:Canvas;--text:CanvasText;--line:color-mix(in srgb, CanvasText 18%, transparent)}body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--surface);color:var(--text);line-height:1.6;padding:24px}main{max-width:720px;margin:0 auto}.card{border:1px solid var(--line);border-radius:16px;padding:18px;margin-top:16px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.08em}@media print{body{padding:0}.card{break-inside:avoid}}</style></head><body><main><p class="eyebrow">oh-my-class template reference</p><h1>${mode.label}</h1><p>${mode.description}</p><section class="card"><h2>Reusable primitives</h2><ul>${primitives}</ul></section><section class="card"><h2>Teacher controls</h2><ul>${controls}</ul></section><section class="card"><h2>Offline adaptation</h2><p>Uses inline CSS, theme/system tokens, no remote assets, and print-safe layout.</p></section></main></body></html>`;
}
