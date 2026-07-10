# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: slide-deck-acceptance-harness.spec.ts >> slide_deck exported HTML — browser QA (SDH-07) >> navigation: next/prev controls advance and rewind the deck
- Location: tests/e2e/slide-deck-acceptance-harness.spec.ts:26:3

# Error details

```
Error: SLIDE_DECK_EXPORT_HTML must point at a real exported HTML file (got: .scratch/slide-deck-acceptance/artifacts/exports/vietnamese_classroom_deck.snap-98ccfc1ffc5c123188ada045.student.html)
```

# Test source

```ts
  1  | import { expect, test } from "@playwright/test";
  2  | import { existsSync } from "node:fs";
  3  | 
  4  | // SDH-07: real browser QA on the *actual exported* standalone slide-deck
  5  | // HTML produced by a real gateway run (services/gateway/tests/
  6  | // test_slide_deck_acceptance_harness.py writes the file and points
  7  | // SLIDE_DECK_EXPORT_HTML at it before invoking `playwright test` with this
  8  | // spec + apps/web/playwright.acceptance.config.ts). No dev server, no mock
  9  | // deck fixture -- this opens the file the harness actually wrote.
  10 | //
  11 | // Selectors match the real standalone player markup proven by
  12 | // packages/renderer/__tests__/slide-deck-standalone-presentation-print-controls.test.ts
  13 | // (data-slide-prev/-next/-progress, role=radiogroup print-mode controls).
  14 | 
  15 | const htmlPath = process.env.SLIDE_DECK_EXPORT_HTML;
  16 | 
  17 | test.beforeAll(() => {
  18 |   if (!htmlPath || !existsSync(htmlPath)) {
> 19 |     throw new Error(
     |           ^ Error: SLIDE_DECK_EXPORT_HTML must point at a real exported HTML file (got: .scratch/slide-deck-acceptance/artifacts/exports/vietnamese_classroom_deck.snap-98ccfc1ffc5c123188ada045.student.html)
  20 |       `SLIDE_DECK_EXPORT_HTML must point at a real exported HTML file (got: ${htmlPath ?? "unset"})`,
  21 |     );
  22 |   }
  23 | });
  24 | 
  25 | test.describe("slide_deck exported HTML — browser QA (SDH-07)", () => {
  26 |   test("navigation: next/prev controls advance and rewind the deck", async ({ page }) => {
  27 |     await page.goto(`file://${htmlPath}`);
  28 |     const next = page.locator("[data-slide-next]").first();
  29 |     const progress = page.locator("[data-slide-progress]").first();
  30 |     await expect(progress).toBeVisible();
  31 |     const before = await progress.textContent();
  32 | 
  33 |     await next.click();
  34 |     await expect
  35 |       .poll(async () => progress.textContent())
  36 |       .not.toBe(before);
  37 | 
  38 |     const prev = page.locator("[data-slide-prev]").first();
  39 |     await prev.click();
  40 |     await expect
  41 |       .poll(async () => progress.textContent())
  42 |       .toBe(before);
  43 |   });
  44 | 
  45 |   test("mobile readability: no horizontal overflow at a 375px viewport", async ({ page }) => {
  46 |     await page.setViewportSize({ width: 375, height: 812 });
  47 |     await page.goto(`file://${htmlPath}`);
  48 |     const overflow = await page.evaluate(
  49 |       () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  50 |     );
  51 |     expect(overflow).toBe(false);
  52 |   });
  53 | 
  54 |   test("print media: every slide is visible, not just the currently active one", async ({ page }) => {
  55 |     await page.goto(`file://${htmlPath}`);
  56 |     await page.emulateMedia({ media: "print" });
  57 | 
  58 |     const slideCount = await page.locator(".slide-card, .slide-frame").count();
  59 |     expect(slideCount).toBeGreaterThan(0);
  60 | 
  61 |     const hiddenUnderPrint = await page.evaluate(() => {
  62 |       const frames = Array.from(document.querySelectorAll<HTMLElement>(".slide-frame, .slide-card"));
  63 |       return frames.filter((frame) => getComputedStyle(frame).display === "none").length;
  64 |     });
  65 |     expect(hiddenUnderPrint).toBe(0);
  66 |   });
  67 | 
  68 |   test("print settings apply: the deck's print-mode selection is reflected in the DOM", async ({ page }) => {
  69 |     await page.goto(`file://${htmlPath}`);
  70 |     const activeOption = page.locator('[data-print-mode-value][aria-checked="true"]').first();
  71 |     await expect(activeOption).toBeVisible();
  72 |     const activeValue = await activeOption.getAttribute("data-print-mode-value");
  73 |     expect(activeValue).toMatch(/^print-mode--(paged-\d|continuous)$/);
  74 | 
  75 |     const rootClass = await page.evaluate(() => document.querySelector("[data-deck-id]")?.className ?? "");
  76 |     expect(rootClass).toContain(activeValue!);
  77 |   });
  78 | });
  79 | 
```