import { expect, test } from "@playwright/test";
import { existsSync } from "node:fs";

// SDH-07: real browser QA on the *actual exported* standalone slide-deck
// HTML produced by a real gateway run (services/gateway/tests/
// test_slide_deck_acceptance_harness.py writes the file and points
// SLIDE_DECK_EXPORT_HTML at it before invoking `playwright test` with this
// spec + apps/web/playwright.acceptance.config.ts). No dev server, no mock
// deck fixture -- this opens the file the harness actually wrote.
//
// Selectors match the real standalone player markup proven by
// packages/renderer/__tests__/slide-deck-standalone-presentation-print-controls.test.ts
// (data-slide-prev/-next/-progress, role=radiogroup print-mode controls).

const htmlPath = process.env.SLIDE_DECK_EXPORT_HTML;

test.beforeAll(() => {
  if (!htmlPath || !existsSync(htmlPath)) {
    throw new Error(
      `SLIDE_DECK_EXPORT_HTML must point at a real exported HTML file (got: ${htmlPath ?? "unset"})`,
    );
  }
});

test.describe("slide_deck exported HTML — browser QA (SDH-07)", () => {
  test("navigation: next/prev controls advance and rewind the deck", async ({ page }) => {
    await page.goto(`file://${htmlPath}`);
    const next = page.locator("[data-slide-next]").first();
    const progress = page.locator("[data-slide-progress]").first();
    await expect(progress).toBeVisible();
    const before = await progress.textContent();

    await next.click();
    await expect
      .poll(async () => progress.textContent())
      .not.toBe(before);

    const prev = page.locator("[data-slide-prev]").first();
    await prev.click();
    await expect
      .poll(async () => progress.textContent())
      .toBe(before);
  });

  test("mobile readability: no horizontal overflow at a 375px viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`file://${htmlPath}`);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflow).toBe(false);
  });

  test("print media: every slide is visible, not just the currently active one", async ({ page }) => {
    await page.goto(`file://${htmlPath}`);
    await page.emulateMedia({ media: "print" });

    const slideCount = await page.locator(".slide-card, .slide-frame").count();
    expect(slideCount).toBeGreaterThan(0);

    const hiddenUnderPrint = await page.evaluate(() => {
      const frames = Array.from(document.querySelectorAll<HTMLElement>(".slide-frame, .slide-card"));
      return frames.filter((frame) => getComputedStyle(frame).display === "none").length;
    });
    expect(hiddenUnderPrint).toBe(0);
  });

  test("print settings apply: the deck's print-mode selection is reflected in the DOM", async ({ page }) => {
    await page.goto(`file://${htmlPath}`);
    const activeOption = page.locator('[data-print-mode-value][aria-checked="true"]').first();
    await expect(activeOption).toBeVisible();
    const activeValue = await activeOption.getAttribute("data-print-mode-value");
    expect(activeValue).toMatch(/^print-mode--(paged-\d|continuous)$/);

    const rootClass = await page.evaluate(() => document.querySelector("[data-deck-id]")?.className ?? "");
    expect(rootClass).toContain(activeValue!);
  });
});
