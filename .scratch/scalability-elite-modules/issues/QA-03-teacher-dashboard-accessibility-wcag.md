# [QA-03] Teacher-dashboard accessibility (WCAG)

Status: TODO
Labels: quality, accessibility
ADR: 034
Depends on: none

## Context

The teacher-facing web app is `apps/web` (Next.js), including the explainable-gate UI (issue #29)
and dashboards for teaching packs, units, vocabulary batches, effectiveness, and approval modals
(see `apps/web/tests/*.test.tsx`). This is the product surface ~1,000 teachers use daily, yet its
**own accessibility has not been audited against WCAG 2.1 AA**. K-12 teachers include users
relying on keyboard navigation, screen readers, and high-contrast/zoom; in the US education
market, ADA/Section 508 expectations around WCAG 2.1 AA are effectively table stakes.

This is **distinct from generated-artifact accessibility** (the accessibility-agent RFC,
`docs/rfc/accessibility-agent.md`), which concerns the *content the pipeline produces*. QA-03 is
about the *app UX itself* — the dashboard, forms, modals, gate UI — being usable by teachers with
disabilities.

## Scope

- [ ] **WCAG 2.1 AA audit** of `apps/web`: run automated checks (e.g. axe) across the key
      surfaces — teaching-pack dashboard, unit dashboard, vocabulary-batch dashboard,
      effectiveness dashboard, approval modal, and the explainable-gate shell/bodies — and pair
      with a manual pass (keyboard-only, screen reader, zoom/contrast). Reuse the existing
      Playwright setup (`apps/web/playwright.config.ts`) for automated a11y assertions.
- [ ] **Fix findings to AA**: remediate contrast, focus management (esp. modals/gate — focus trap,
      return focus, Esc), keyboard operability of all interactive controls, semantic
      roles/labels/ARIA, form labels + error association, heading structure/landmarks, and
      accessible names for icon-only controls.
- [ ] **Modal + gate focus correctness**: the approval modal and explainable-gate flows must trap
      focus while open, restore focus on close, and be fully operable by keyboard and announced to
      screen readers (these interactive flows are the highest-risk surfaces).
- [ ] **Automated a11y regression tests**: add axe-based assertions to the component/Playwright
      test suites (`apps/web/tests/`) so new violations fail CI — accessibility becomes a
      standing gate, not a one-time cleanup.
- [ ] **Document conformance**: record the target (WCAG 2.1 AA), the audited surfaces, known
      gaps/exceptions, and how it's kept from regressing.
- [ ] Explicitly **scope to the app UX**, not generated artifacts — cross-reference the
      accessibility-agent RFC so the two efforts don't overlap or leave a gap.

## Acceptance

- Automated axe checks on the key `apps/web` surfaces report zero WCAG 2.1 AA violations (or
  documented, justified exceptions).
- Keyboard-only and screen-reader passes confirm all interactive flows — including the approval
  modal and explainable gate — are operable and announced, with correct focus trap/return.
- axe-based a11y assertions are wired into `apps/web/tests/` and fail CI on new violations.
- A conformance note documents target, audited surfaces, exceptions, and the regression gate.
- The work is scoped to app UX and cross-references the accessibility-agent RFC for artifact
  content.

## References

- `apps/web/` — Next.js teacher app (`middleware.ts`, `next.config.ts`, `playwright.config.ts`,
  `vitest.config.ts`).
- `apps/web/tests/*.test.tsx` — existing component tests (dashboards, `approval-modal`,
  `teaching-pack-gate-shell`, `teaching-pack-gate-bodies-render`, etc.) to extend with a11y checks.
- Issue #29 (explainable gate UI) — a key interactive surface.
- `docs/rfc/accessibility-agent.md` — generated-artifact accessibility (distinct effort).
- ADR-034 decision 11.

## Implementation notes

- Automated tools catch ~30-40% of issues; the manual keyboard/screen-reader pass is where modal
  and gate focus bugs surface — budget for both.
- The approval modal and explainable gate are the highest-risk surfaces (dynamic, focus-sensitive)
  — prioritize them.
- Wire axe into the existing Playwright/vitest suites rather than standing up a new harness, so the
  a11y gate lives with the tests teachers' flows already have.
- Keep firmly out of scope: the accessibility of pipeline-*generated* content (that's the
  accessibility-agent RFC) — this issue is the app the teacher clicks through.
