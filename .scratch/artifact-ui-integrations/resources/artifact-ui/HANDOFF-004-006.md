# Artifact UI — Issues 004–006 Handoff

Companion to `HANDOFF.md` (Issues 001–003). That handoff's §6 flagged the
wiring debt this one closes: "small interactive scripts the reference
templates ship ... no inline `<script>` wiring was written." Issues
004–006 are now implemented — `README-issues-004-006.md`'s original
framing ("proposal only, nothing implemented") is superseded by this file.

## Issue 004 — Core primitives for root-cause / Socratic teaching

7 new family-agnostic primitives added to `primitives.css`: anchor
timeline, controlled comparison, scenario anchor, generalization
checkpoint, stress test, metaphor log, mastery marker. Typed inputs and
classes cataloged in `docs/component-reference.md` §2. Demoed (partially
— see that file's own note) in `dist/core-primitives.html`.

## Issue 005 — Root-Cause Session dossier

First real end-to-end artifact on Issue 004's primitives:
`dist/families/root-cause-session.html`, Paper Dossier family (§10.5's
default held — no 5th family needed). Content follows one real
`rooted-in-strength-learning` transcript (Future Perfect vs. Future
Perfect Continuous), per `README-issues-004-006.md`. Screenshot QA at
375/768/1280: `qa/screenshots/root-cause-session-{375,768,1280}.png`.

## Issue 006 — Interactivity layer

| AC | Status |
|---|---|
| Close Issue 003 debt: `.art-reveal-btn`, `.art-mode-toggle`, `.art-jumpbox` | Done — `pages/exam-key.js` now passes `script: INTERACTIVITY_JS` to `renderPage()` (previously imported but never used, so none of this markup was functional despite already having the right `data-*`/CSS). Bulk mode-toggle, per-question reveal, jumpbox go-button, and the `.art-qgrid` shortcut buttons (previously dead — no `data-jump-to` at all despite `cursor:pointer` styling) are all wired now. |
| Wire `.art-generalization-checkpoint` (one-way reveal) | Done — `data-hide-after-reveal`; verdict is authored content revealed on click, not graded |
| Wire exception/wrinkle reveal | Done — `renderExceptionReveal()` in `partials.js`, composed from existing `.art-callout--dashed` + `.art-reveal-btn` per contract 1, not a new primitive |
| Wire `.art-metaphor-log` expand/collapse | Done — landed attempt stays visible by default; earlier attempts gated |
| `.art-mastery-marker` — hold off | Done (i.e. correctly left un-wired) — static chip only, per the issue's own reasoning about rendering an already-completed session |
| No persistence, no client-side grading, no new primitives | Confirmed by construction — see `interactivity.js`'s own "non-goals" comment |
| Keyboard-reachable, visible focus state | Verified live, not just asserted — `qa/shot_issue006.py` tabs from page load with no mouse and confirms it lands on a `[data-toggle-reveal]` button, then activates it with `Enter` (not a click) and confirms `aria-expanded` flips. |
| `prefers-reduced-motion` respected, content still reachable | Verified live — `qa/shot_issue006.py` emulates `reduced-motion: reduce` and confirms: `.art-flash` does NOT apply, `.art-jump-highlight` (the load-bearing, non-decorative feedback) STILL applies, and a reveal still un-hides its panel. This caught that `.art-jump-highlight` had no CSS rule at all before this pass — see below. |
| Grep-verified: no remote resource, no `eval` | Done — `grep -n "http://\|https://\|eval(" dist/families/exam-key.html dist/families/root-cause-session.html dist/core-primitives.html` → 0 matches |
| Screenshot QA at 375/768/1280, both states (not just default) | Done — `qa/screenshots/exam-key-default-{375,768,1280}.png` (exam-key had never been screenshotted at all before this pass) + `exam-key-revealed-{375,768,1280}.png`, `root-cause-session-revealed-{375,768,1280}.png` (existing `root-cause-session-*` shots were all default-state only), plus targeted 768px shots for the mode-toggle bulk action, jumpbox landing, and the newly-wired qgrid shortcut. |
| Re-run the "does mobile layout actually work" check | Done — all screenshots above inspected at 375px; no overflow/clipping regressions found this pass (unlike Issue 001's original core-primitives pass, which did find one) |

### A real bug this pass's QA caught

`interactivity.js` applies `.art-jump-highlight` to every jump target as
its unconditional, reduced-motion-safe feedback — but no CSS anywhere
defined that class. Before this fix, a reduced-motion user landing on a
jump target got no visual feedback at all (only the default browser
focus ring, and only if the target itself was focusable). Fixed in
`primitives.css` (kept family-agnostic, next to `.art-reveal-target`,
since the jump-to-target contract itself is family-agnostic even though
its only current consumer — exam-key's dense nav — is paper-dossier).
Caught by the reduced-motion Playwright check, not by code review.

### Also fixed this pass (same debt category, not called out by name in the issue's own AC)

- `art-no-print` was missing from several controls that only make sense
  on a screen: the exception-reveal button, the metaphor-log
  expand/collapse toggle, and (in `exam-key.js`) the per-question reveal
  button, the jumpbox and its go-button/status line, and the mode-toggle
  switch. `.art-generalization-checkpoint`'s reveal button already had
  it; the others didn't. All verified in an emulated `print` media query
  (`qa/shot_issue006.py`): the four screen-only controls now compute
  `display: none`, and an un-clicked answer panel still renders in print
  (`.art-reveal-target[hidden] { display: revert !important }` under
  `@media print`, already in `primitives.css` from this same issue).
- `.art-qgrid`'s per-question shortcut buttons were markup-only — no
  `data-jump-to`, despite already being styled `cursor: pointer` and
  despite `interactivity.js`'s own contract-3 doc comment naming "a
  question-grid shortcut" as the intended use case. Wired to `data-jump-to="${q.n}"`.

### Docs updated

- `docs/component-reference.md` — new §6a, interactivity contract
  reference + which components use each contract.
- `docs/DESIGN.md` — new §10.7, points back to §6/§7 (motion,
  accessibility) and explains this is an addition to those rules, not an
  exception to them.

### Verification script

`qa/shot_issue006.py` — real headless-Chromium (Playwright), not a
permanent build step. Re-run with:

```
cd resources/artifact-ui
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python3 qa/shot_issue006.py
```

### Explicitly still open (not this issue's scope)

- Issue 005's `.art-section--tight` follow-up (DESIGN.md §10.5) —
  pacing/spacing only, not interactivity.
- Porting `pages/*.js` into real Eta templates — unchanged from
  `HANDOFF.md` §6.
- No automated test suite committed; verification this pass is the
  Playwright script above plus the grep checks in the AC table, same
  "ad hoc, not committed tests" posture as `HANDOFF.md` §4.
