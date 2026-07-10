import { defineConfig, devices } from "@playwright/test";

// SDH-07: browser QA for the slide-deck real-LLM acceptance harness.
// Deliberately separate from playwright.config.ts -- this suite opens a
// standalone exported HTML file directly (file://), so it must NOT boot the
// `pnpm dev` webServer that config declares for the app's own e2e specs.
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /slide-deck-acceptance-harness\.spec\.ts/,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } } },
    { name: "mobile", use: { ...devices["Desktop Chrome"], viewport: { width: 375, height: 812 } } },
  ],
});
