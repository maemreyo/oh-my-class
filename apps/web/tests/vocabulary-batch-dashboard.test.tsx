import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { VocabularyBatchDashboard } from "@/components/vocabulary-batch-dashboard";
import type { VocabularyBatchDashboardCluster } from "@/components/vocabulary-batch-dashboard";

function clusters(count: number): VocabularyBatchDashboardCluster[] {
	return Array.from({ length: count }, (_, index) => {
		const status = index % 10 === 0 ? "failed" : index % 4 === 0 ? "needs_review" : "passed";
		return {
			cluster_id: `cluster-${index + 1}`,
			title: `Cluster ${index + 1}`,
			terms: [`term-${index + 1}-a`, `term-${index + 1}-b`],
			review_status: status,
			warnings: status === "needs_review" ? ["Teacher review required before student export."] : [],
			exportedFiles: status === "passed" ? [`clusters/cluster-${index + 1}/teaching-student.html`] : [],
		};
	});
}

describe("VocabularyBatchDashboard", () => {
	it("renders medium-batch progress and status navigation readably", () => {
		const html = renderToStaticMarkup(
			<VocabularyBatchDashboard clusters={clusters(25)} selectedClusterIds={["cluster-5"]} />,
		);

		expect(html).toContain("25 clusters");
		expect(html).toContain("Batch progress");
		expect(html).toContain("Cluster status navigation");
		expect(html).toContain("Needs review");
		expect(html).toContain("Failed");
		expect(html).toContain("Teacher review required before student export.");
		expect(html).toContain("Included in selected export");
		expect(html).toContain("Withheld until review or excluded from selected export");
		expect(html).not.toContain("Traceback");
	});

	it("handles 100 clusters without dropping later entries", () => {
		const html = renderToStaticMarkup(<VocabularyBatchDashboard clusters={clusters(100)} />);

		expect(html).toContain("100 clusters");
		expect(html).toContain("Cluster 100");
		expect(html).toContain("term-100-a, term-100-b");
	});
});
