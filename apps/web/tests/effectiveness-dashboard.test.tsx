import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { EffectivenessDashboard } from "@/components/effectiveness-dashboard";

describe("EffectivenessDashboard", () => {
	it("renders aggregate improvement signals without evaluation language", () => {
		const html = renderToStaticMarkup(
			<EffectivenessDashboard
				current={{ averageMastery: 0.74, learnerCount: 25, learnersDat: 17 }}
				previous={{ averageMastery: 0.68, learnerCount: 25, learnersDat: 16 }}
			/>,
		);

		expect(html).toContain("Average mastery");
		expect(html).toContain("% đạt");
		expect(html).toContain("Trend");
		expect(html).toContain("74%");
		expect(html).toContain("68%");
		expect(html).toContain("+6 pts");
		expect(html).toContain("aggregate and advisory");
		expect(html).not.toMatch(/chuẩn xếp loại|teacher evaluation|single-pack verdict/i);
		expect(html).not.toMatch(/0\.4\s*\*|vendor/i);
	});
});
