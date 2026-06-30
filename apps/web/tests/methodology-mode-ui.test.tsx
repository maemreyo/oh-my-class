import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import {
	METHODOLOGY_MODES,
	classifyMethodologyPair,
	combinedPreviewMetadata,
	modeByTag,
} from "@/components/methodology/mode-registry";
import { METHODOLOGY_REGISTRY } from "@oh-my-class/schemas";
import {
	MethodologyInspectorPanel,
	MethodologyModePicker,
	MethodologyPreviewShell,
} from "@/components/methodology/mode-surfaces";
import {
	updateTimedQuizSettings,
	validateTimedQuizDuration,
} from "@/components/methodology/timed-quiz-controls";
import { TEMPLATE_REFERENCE_MODES } from "@/components/methodology/template-reference-modes";

describe("MethodologyModePicker", () => {
	it("renders all supported modes with accessible labels and descriptions", () => {
		const html = renderToStaticMarkup(<MethodologyModePicker selectedTag="standard" />);

		for (const mode of METHODOLOGY_MODES) {
			expect(html).toContain(mode.label);
			expect(html).toContain(mode.description);
		}
	});

	it("marks selected and disabled mode states", () => {
		const html = renderToStaticMarkup(
			<MethodologyModePicker selectedTag="inverse_thinking" disabledTags={["film_based"]} />,
		);

		expect(html).toContain("aria-pressed=\"true\"");
		expect(html).toContain("disabled=\"\"");
	});

	it("uses shared mode data instead of hidden literals", () => {
		expect(modeByTag("why_wrong_reasoning")?.label).toBe("Why Wrong Reasoning");
		expect(modeByTag("future_mode")).toBeNull();
	});

	it("renders template reference modes as disabled coming-soon picker entries", () => {
		const disabledTags = TEMPLATE_REFERENCE_MODES.map((mode) => mode.tag);
		const html = renderToStaticMarkup(
			<MethodologyModePicker selectedTag="standard" disabledTags={disabledTags} />,
		);

		for (const mode of TEMPLATE_REFERENCE_MODES) {
			expect(html).toContain(mode.label);
			expect(html).toContain("Coming soon as a tokenized reference mode");
		}
		expect(html.match(/disabled=""/g)?.length).toBeGreaterThanOrEqual(TEMPLATE_REFERENCE_MODES.length);
	});

	it("renders each generated registry tag exactly once", () => {
		const modeTags = METHODOLOGY_MODES.map((mode) => mode.tag);

		for (const entry of METHODOLOGY_REGISTRY) {
			expect(modeTags.filter((tag) => tag === entry.tag)).toHaveLength(1);
		}
	});

	it("disables conflicted combinations with teacher-readable rationale", () => {
		const html = renderToStaticMarkup(
			<MethodologyModePicker selectedTag="shy_student_1on1" selectedTags={["shy_student_1on1"]} />,
		);

		expect(classifyMethodologyPair("shy_student_1on1", "timed_quiz")).toBe("conflict");
		expect(html).toContain("Timed Quiz");
		expect(html).toContain("timed public pressure does not fit private rehearsal flows");
	});

	it("allows compatible inverse thinking plus active recall and shows combined preview metadata", () => {
		const html = renderToStaticMarkup(
			<MethodologyModePicker selectedTag="inverse_thinking" selectedTags={["inverse_thinking", "active_recall"]} />,
		);

		expect(classifyMethodologyPair("inverse_thinking", "active_recall")).toBe("compatible");
		expect(combinedPreviewMetadata(["inverse_thinking", "active_recall"])).toContain("Inverse Thinking + Active Recall");
		expect(html).toContain("Combined preview: Inverse Thinking + Active Recall");
		expect(html).toContain("aria-pressed=\"true\"");
	});
});

describe("MethodologyInspectorPanel", () => {
	it("groups pass warning and fail statuses with jump links", () => {
		const html = renderToStaticMarkup(
			<MethodologyInspectorPanel
				declaredTags={["inverse_thinking", "concept_map", "future_mode"]}
				requirements={[
					{ tag: "inverse_thinking", component: "case_flow", status: "pass", jumpHref: "#case" },
					{ tag: "concept_map", component: "concept_map", status: "fail", jumpHref: "#concept" },
				]}
				warnings={[{ severity: "warning", message: "Generic disaster", jumpHref: "#disaster" }]}
			/>,
		);

		expect(html).toContain("Pass");
		expect(html).toContain("Warning");
		expect(html).toContain("Fail");
		expect(html).toContain("future_mode");
		expect(html).toContain("href=\"#disaster\"");
	});

	it("explains Concept Map accepted component alternatives", () => {
		const html = renderToStaticMarkup(
			<MethodologyInspectorPanel
				declaredTags={["concept_map"]}
				requirements={[{ tag: "concept_map", component: "vocab_cluster or contrastive_pairs", status: "fail", jumpHref: "#concept-map" }]}
			/>,
		);

		expect(html).toContain("Concept Map");
		expect(html).toContain("vocab_cluster");
		expect(html).toContain("contrastive_pairs");
		expect(html).toContain("vocabulary cluster or contrastive-pair structure");
	});

	it("shows Contrastive Pairs title, side labels, and satisfaction", () => {
		const html = renderToStaticMarkup(
			<MethodologyInspectorPanel
				declaredTags={["contrastive_pairs"]}
				requirements={[{ tag: "contrastive_pairs", component: "contrastive_pairs", status: "pass", jumpHref: "#contrast" }]}
				details={{ contrastivePair: { title: "Because vs Although", leftLabel: "Because", rightLabel: "Although", reason: "Students confuse reason and contrast connectors." } }}
			/>,
		);

		expect(html).toContain("Because vs Although");
		expect(html).toContain("Because");
		expect(html).toContain("Although");
		expect(html).toContain("Students confuse reason and contrast connectors.");
		expect(html).toContain("contrastive_pairs: contrastive_pairs");
	});

	it("shows Film Based clip context and component satisfaction", () => {
		const html = renderToStaticMarkup(
			<MethodologyInspectorPanel
				declaredTags={["film_based"]}
				requirements={[{ tag: "film_based", component: "film_clip_activity", status: "pass", jumpHref: "#film" }]}
				details={{ filmActivity: { title: "Bus stop scene", context: "Students infer connector purpose from a short classroom clip.", before: "Predict the connector.", during: "Listen for because and although.", after: "Explain the speaker purpose." } }}
			/>,
		);

		expect(html).toContain("Bus stop scene");
		expect(html).toContain("Students infer connector purpose");
		expect(html).toContain("Before watching");
		expect(html).toContain("While watching");
		expect(html).toContain("After watching");
		expect(html).toContain("film_based: film_clip_activity");
	});

	it("shows Shy Student 1:1 intent, roleplay status, and coaching separation", () => {
		const html = renderToStaticMarkup(
			<MethodologyInspectorPanel
				declaredTags={["shy_student_1on1"]}
				requirements={[{ tag: "shy_student_1on1", component: "roleplay_script", status: "pass", jumpHref: "#roleplay" }]}
				details={{ shyStudent: { intent: "Low-pressure private rehearsal before any sharing.", requiredComponent: "roleplay_script", coachingNotesSeparated: true } }}
			/>,
		);

		expect(html).toContain("Shy Student 1:1");
		expect(html).toContain("Low-pressure private rehearsal");
		expect(html).toContain("roleplay_script");
		expect(html).toContain("Teacher-only coaching notes separated");
		expect(html).toContain("shy_student_1on1: roleplay_script");
	});

	it("shows Active Recall retrieval-practice intent and prompt satisfaction", () => {
		const html = renderToStaticMarkup(
			<MethodologyInspectorPanel
				declaredTags={["active_recall"]}
				requirements={[{ tag: "active_recall", component: "active_recall_prompt", status: "pass", jumpHref: "#recall" }]}
				details={{ activeRecall: { intent: "Students retrieve from memory before seeing support.", requiredComponent: "active_recall_prompt", revealSeparated: true } }}
			/>,
		);

		expect(html).toContain("Active Recall");
		expect(html).toContain("Students retrieve from memory");
		expect(html).toContain("active_recall_prompt");
		expect(html).toContain("Reveal and rationale separated");
		expect(html).toContain("active_recall: active_recall_prompt");
	});

	it("shows Why Wrong Reasoning coverage, missing distractors, and editor fields", () => {
		const html = renderToStaticMarkup(
			<MethodologyInspectorPanel
				declaredTags={["why_wrong_reasoning"]}
				requirements={[{ tag: "why_wrong_reasoning", component: "wrong_reasons", status: "fail", jumpHref: "#question-card-q2-wrong-reasons" }]}
				details={{
					whyWrongReasoning: {
						questions: [{ id: "q2", prompt: "Which connector fits?", options: { A: "because", B: "although", C: "and" }, answer: "B", wrongReasons: { A: "A gives a cause, not a contrast." } }],
					},
				}}
			/>,
		);

		expect(html).toContain("Why Wrong Reasoning");
		expect(html).toContain("question-card-q2-wrong-reasons");
		expect(html).toContain("Missing wrong reason for C");
		expect(html).toContain("Wrong reason for A");
		expect(html).toContain("A gives a cause, not a contrast.");
	});

	it("shows Timed Quiz duration controls, timing metadata coverage, and warning jump links", () => {
		const html = renderToStaticMarkup(
			<MethodologyInspectorPanel
				declaredTags={["timed_quiz"]}
				requirements={[{ tag: "timed_quiz", component: "time_limit", status: "warning", jumpHref: "#timed-quiz-duration" }]}
				details={{ timedQuiz: { settings: { durationMinutes: 8, intensity: "balanced" }, timedItemCount: 2, totalItemCount: 3 } }}
			/>,
		);

		expect(html).toContain("Timed Quiz");
		expect(html).toContain("Duration minutes");
		expect(html).toContain("Balanced");
		expect(html).toContain("2 of 3 items include time badges");
		expect(html).toContain("href=\"#timed-quiz-duration\"");
		expect(html).toContain("Preview metadata: 8 minutes, balanced intensity.");
	});
});

describe("Timed Quiz controls", () => {
	it("updates preview metadata settings and rejects invalid durations", () => {
		const updated = updateTimedQuizSettings({ durationMinutes: 8, intensity: "balanced" }, { durationMinutes: 12, intensity: "challenge" });

		expect(updated).toEqual({ durationMinutes: 12, intensity: "challenge" });
		expect(validateTimedQuizDuration(12)).toEqual([]);
		expect(validateTimedQuizDuration(0)).toContain("timed_quiz.duration_minutes");
		expect(validateTimedQuizDuration(181)).toContain("timed_quiz.duration_minutes");
	});
});

describe("MethodologyPreviewShell", () => {
	it("renders standalone HTML in restrictive iframe with viewport controls", () => {
		const html = renderToStaticMarkup(
			<MethodologyPreviewShell html="<!DOCTYPE html><html><body>oh-my-class</body></html>" width="tablet" />,
		);

		expect(html).toContain("Desktop");
		expect(html).toContain("Tablet");
		expect(html).toContain("Mobile");
		expect(html).toContain("sandbox=\"allow-same-origin\"");
		expect(html).not.toContain("allow-scripts");
	});
});
