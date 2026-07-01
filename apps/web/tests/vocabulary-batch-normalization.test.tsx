import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { VocabularyBatchNormalizationPreview } from "@/components/vocabulary-batch-normalization-preview";

describe("VocabularyBatchNormalizationPreview", () => {
	it("shows ready and ambiguous clusters separately", () => {
		const html = renderToStaticMarkup(
			<VocabularyBatchNormalizationPreview
				report={{
					report_id: "norm-1",
					ready_clusters: [
						{
							cluster_id: "cluster-1",
							terms: ["travel", "journey", "trip"],
							raw_input_span: "travel / journey / trip",
							title_hint: "Travel words",
							notes: ["Nhấn journey khác trip"],
							confidence: 0.94,
						},
					],
					ambiguous_clusters: [
						{
							span_id: "ambiguous-1",
							raw_input_span: "bank",
							terms: ["bank"],
							reason: "Only one term was found.",
							confidence: 0.35,
						},
					],
					clarifying_questions: ["For ‘bank’, what terms should it be contrasted with?"],
					skipped_spans: [],
					parse_confidence: 0.71,
				}}
			/>,
		);

		expect(html).toContain("Ready clusters");
		expect(html).toContain("Ambiguous spans");
		expect(html).toContain("Travel words");
		expect(html).toContain("travel, journey, trip");
		expect(html).toContain("For ‘bank’, what terms should it be contrasted with?");
		expect(html).not.toContain("Traceback");
	});
});
