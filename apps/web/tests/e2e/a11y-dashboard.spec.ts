import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.describe("dashboard accessibility", () => {
	test.setTimeout(60_000);

	test("runs/new has no WCAG 2.2 AA violations", async ({ page }) => {
		await page.goto("/runs/new");
		await expect(page.getByRole("heading", { name: "Build a teaching pack" })).toBeVisible();

		const results = await new AxeBuilder({ page })
			.withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
			.analyze();

		expect(results.violations).toEqual([]);
	});
});
