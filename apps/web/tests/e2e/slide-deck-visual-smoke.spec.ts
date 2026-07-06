import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { renderArtifact } from "../../../../packages/renderer/src/renderer";
import type { SlideDeckData } from "../../../../packages/renderer/src/contracts";

const fixturePath = resolve(process.cwd(), "../../.scratch/slide-deck-engine/fixtures/golden/interaction-deck.json");

function loadDeck(): SlideDeckData {
  return JSON.parse(readFileSync(fixturePath, "utf-8")) as SlideDeckData;
}

test.describe("slide_deck visual smoke", () => {
  test("student surface has no overflow and preserves interaction fallback", async ({ page }) => {
    const html = await renderArtifact("slide_deck", { ...loadDeck(), render_surface: "student" });
    await page.setContent(html, { waitUntil: "domcontentloaded" });

    await expect(page.getByRole("heading", { name: "Quick Check" })).toBeVisible();
    await expect(page.getByText("No-JS fallback: Students hold up A, B, or C cards.")).toBeVisible();
    await expect(page.getByText("2/4 simplifies to 1/2.")).toHaveCount(0);

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(overflow).toBe(false);
  });

  test("teacher surface reveals answer guidance and focus remains visible", async ({ page }) => {
    const html = await renderArtifact("slide_deck", { ...loadDeck(), render_surface: "teacher" });
    await page.setContent(`<button>Before deck</button>${html}<button>After deck</button>`, { waitUntil: "domcontentloaded" });

    await expect(page.getByText("Teacher guide").first()).toBeVisible();
    await expect(page.getByText("2/4 simplifies to 1/2.")).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(page.getByRole("button", { name: "Before deck" })).toBeFocused();
  });

  test("print surface expands reveals and supports dark color scheme", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    const html = await renderArtifact("slide_deck", { ...loadDeck(), render_surface: "print" });
    await page.setContent(html, { waitUntil: "domcontentloaded" });

    await expect(page.getByText("Print handout")).toBeVisible();
    await expect(page.getByText("Slide 1 · all at once")).toBeVisible();
    const bodyBackground = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    expect(bodyBackground).not.toBe("rgba(0, 0, 0, 0)");
  });
});
