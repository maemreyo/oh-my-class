---
title: Test and CI foundation for mode readiness
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add the missing testing infrastructure that multiple mode issues depend on: renderer Vitest harness, Playwright visual/responsive checks, schema parity CI, fixture reuse, coverage thresholds, and hard-invariant property tests. Exploration found AGENTS.md mandates these gates, but the issue set currently mentions them piecemeal rather than owning the shared infrastructure.

This issue should not implement inverse-thinking behavior. It creates the common testing foundation so 001-025 can be verified consistently.

## Acceptance criteria

- [ ] `packages/renderer` has a Vitest harness and package script for renderer tests.
- [ ] `apps/web` has Playwright configuration for 375/768/1280/1920 viewports and print/dark-mode checks.
- [ ] CI runs schema generation/parity checks (`generate:schemas`, `verify:schemas`, `verify:frontend-api`) on contract changes.
- [ ] Coverage gates align with AGENTS.md targets: agents ≥85%, contracts ≥95%, renderer ≥90%, quality ≥90%.
- [ ] Shared fixture factories exist for contracts, artifacts, quality gates, and inverse-thinking packs.
- [ ] Quality hard-block property tests cover missing DOCTYPE, external assets, answer-key leakage, native radio inputs, unmanaged JS runtime, and missing brand string.

## Detailed test suite

- [ ] `pnpm -F @oh-my-class/renderer test` or equivalent runs and fails if standalone renderer invariants regress.
- [ ] `pnpm -F web test:e2e` runs Playwright against at least one dashboard route and one rendered artifact fixture at the four mandated widths.
- [ ] CI workflow test/documentation: Contract changes trigger schema generation and parity verification.
- [ ] `uv run pytest packages/quality -m property -v`: Property tests generate adversarial HTML and each hard-block detector fires at least once.
- [ ] `uv run pytest common/contracts/tests -v --cov=common/contracts --cov-fail-under=95` passes.
- [ ] `pnpm test:coverage` or equivalent reports renderer coverage ≥90% once renderer tests exist.
- [ ] Golden fixture test: Rendering canonical fixtures produces stable output, and intentional brand/DOCTYPE/external-asset regressions fail.

## Blocked by

None - can start immediately
