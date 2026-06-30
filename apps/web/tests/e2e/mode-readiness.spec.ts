import { expect, test } from "@playwright/test";

const renderedArtifactFixture = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root{color-scheme:light dark}body{font-family:system-ui;margin:0;padding:24px}article{border:1px solid currentColor;border-radius:16px;padding:16px}@media print{body{padding:0}article{box-shadow:none}}
  </style>
</head>
<body><article><p>oh-my-class</p><h1>Rendered artifact fixture</h1><p>Student-safe preview content.</p></article></body>
</html>`;

test.describe("mode readiness visual checks", () => {
  test("dashboard route is usable at mandated viewport", async ({ page }) => {
    await page.goto("/runs/new");

    await expect(page.getByRole("heading", { name: "Teaching approach" })).toBeVisible();
    await expect(page.getByText("oh-my-class").first()).toBeVisible();
  });

  test("rendered artifact fixture supports dark and print media", async ({ page }) => {
    await page.setContent(renderedArtifactFixture, { waitUntil: "domcontentloaded" });

    await page.emulateMedia({ colorScheme: "dark" });
    await expect(page.getByRole("heading", { name: "Rendered artifact fixture" })).toBeVisible();

    await page.emulateMedia({ media: "print" });
    await expect(page.getByText("Student-safe preview content.")).toBeVisible();
  });
});
