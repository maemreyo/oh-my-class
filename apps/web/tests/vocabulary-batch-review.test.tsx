import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import {
	applyVocabularyClusterFieldEdit,
	buildVocabularyPreferenceEvent,
	VocabularyBatchReviewEditor,
} from "@/components/vocabulary-batch-review-editor";
import type { PracticeSet, SemanticAnchorCluster } from "@oh-my-class/schemas";

const cluster: SemanticAnchorCluster = {
	cluster_id: "cluster-travel",
	title: "Travel words",
	title_confidence: 0.76,
	raw_input_span: "travel / journey / trip",
	terms: ["travel", "journey", "trip"],
	anchors: [
		{
			word: "journey",
			impression_vi: "Một hành trình có trải nghiệm.",
			core_trigger_en: "meaningful movement",
			visual_cue_vi: "Đường dài với nhiều cột mốc.",
			semantic_chain: ["move", "experience"],
			example_en: "The journey changed her.",
			contrast_note_vi: "Trip cụ thể hơn journey.",
			student_explanation_vi: "Journey nhấn vào quá trình và trải nghiệm.",
			teacher_script_vi: "Ask for what changed during the movement.",
			edge_cases: ["business trip is more natural"],
			source_notes: ["teacher-only dictionary note"],
		},
	],
	contrast_notes: ["Trip names a specific visit."],
	summary_rows: ["Journey is about the process."],
	review_status: "needs_review",
	warnings: ["Needs teacher confirmation before student export."],
	teacher_source_notes: ["teacher-only source note"],
};

const practiceSet: PracticeSet = {
	practice_set_id: "practice-travel",
	cluster_id: "cluster-travel",
	items: [
		{
			item_id: "practice-1",
			intent: "core_trigger_recall",
			prompt: "Which word focuses on the process?",
			answer: "journey",
			rationale: "Journey emphasizes the process and experience.",
		},
	],
};

describe("VocabularyBatchReviewEditor", () => {
	it("renders cluster status, warnings, previews, and withheld student export state", () => {
		const html = renderToStaticMarkup(
			<VocabularyBatchReviewEditor clusters={[cluster]} practiceSets={[practiceSet]} />,
		);

		expect(html).toContain("Structured cluster editor");
		expect(html).toContain("needs_review · 1 practice items");
		expect(html).toContain("Student export withheld until a teacher approves this needs_review cluster.");
		expect(html).toContain("Needs teacher confirmation before student export.");
		expect(html).toContain("Teacher scripts, source notes, answers, and rationales are hidden here.");
		expect(html).not.toContain("Journey emphasizes the process and experience.");
		expect(html).not.toContain("teacher-only source note");
	});

	it("edits validated contract fields and records teacher preference events", () => {
		const edited = applyVocabularyClusterFieldEdit(cluster, "summary_rows.0", "Journey = process plus experience");
		const event = buildVocabularyPreferenceEvent(cluster, "summary_rows.0", "Journey = process plus experience");

		expect(edited.summary_rows[0]).toBe("Journey = process plus experience");
		expect(event).toEqual({
			clusterId: "cluster-travel",
			fieldPath: "summary_rows.0",
			previousValue: "Journey is about the process.",
			nextValue: "Journey = process plus experience",
		});
	});

	it("exposes approve decisions that unlock needs_review only after teacher action", () => {
		const onDecisionAction = vi.fn();
		const html = renderToStaticMarkup(
			<VocabularyBatchReviewEditor clusters={[cluster]} practiceSets={[practiceSet]} onDecisionAction={onDecisionAction} />,
		);

		expect(html).toContain("Approve cluster");
		expect(onDecisionAction).not.toHaveBeenCalled();
	});
});
