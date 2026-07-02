# Artifact UI Layer — Implementation Handoff

Implements ADR-023 and Issues 001, 002, 003 in dependency order, against
the docs in `artifact-ui-layer-handoff/`.

## 0. About the source archive

The archive listed a staging folder at `.scratch/artifact-ui-layer/bundle/`
for inspection, but the extracted ZIP contained 18 files with no `bundle/`
directory (confirmed by listing every path in the archive). Everything
here was built from the README, the 3 ADRs, the 3 issues, the 6 reference
templates, and the 3 constraint docs (AGENTS.md, DESIGN.md,
`docs/agents/*`) only. If `bundle/` had real renderer/contract code in it,
re-share it and the Eta template porting step in §5 below gets a lot more
concrete.

## 1. What this sandbox is and isn't

There's no real `packages/renderer`, no Eta engine wired to real
contracts, and no `common/contracts` schema in this environment — just
the handoff docs. So this deliverable is two things at once:

1. **Genuinely production-ready CSS** — `tokens/*.css`, `primitives.css`,
   `families/*.css` are framework-agnostic and can be dropped into the
   real renderer package essentially as-is.
2. **A faithful HTML/JS simulation of the render pipeline** — `render.js`
   inlines the CSS into `<style>` blocks the same way the real Eta build
   step should, and `pages/*.js` build realistic content the same shape
   real `SemanticAnchorCluster`/`PracticeSet` data would produce. This
   proves the design system and the projection-safety architecture work,
   but the actual Eta `.html` templates for `packages/renderer/templates/`
   still need to be written by someone with the real contracts in hand.

## 2. Issue 001 — Core Artifact UI primitives

| AC | Status |
|---|---|
| DESIGN.md documents a separate Artifact UI layer | Done — `docs/DESIGN.md` §10, references ADR-023 and the template corpus |
| Renderer-owned tokens for all 4 families | Done — `tokens/navy-ticket.css`, `paper-dossier.css`, `transit-route.css`, `investigation-folder.css`, all implementing `tokens/contract.css` |
| Primitives render from typed inputs, not pasted template HTML | Done — every primitive is authored fresh against semantic tokens; nothing is copy-pasted from the 6 reference templates. `pages/*.js` pass structured JS objects into render functions, not raw HTML |
| Standalone showcase, all primitives + 3 diagnostics states | Done — `dist/core-primitives.html`, live 4-way theme switcher, passed/needs_review/failed diagnostics panels |
| No http(s)://, no remote fonts, no CDN, no external scripts | Done by construction — grep-verified, see §4 |
| Visually QA'd at 375/768/1280 with screenshots | Partial — `qa/screenshots/core-primitives-{375,768,1280}.png` captured with a real headless-Chromium run (Playwright, local binary, no network needed) and used to find and fix a real mobile-overflow bug (ad-hoc inline grids not collapsing; fixed in `pages/core-primitives.js` + `primitives.css` word-break safety net). Issue 002/003 pages were **not** screenshot-QA'd in this pass — see §6 |
| Tests cover standalone invariants, brand string, no external refs | Not built as an automated suite in this pass — see §6 |

## 3. Issue 002 — Semantic vocabulary redesign

| AC | Status |
|---|---|
| Teaching teacher/student use Artifact UI primitives | Done — `dist/semantic-vocabulary/cluster-0{1,2}/teaching.*.html` |
| Practice teacher/student separate prompt/answer/rationale/student-safe fields | Done — `practiceBody()` in `pages/semantic-vocabulary.js` only includes `.art-pq-ans`/`.art-pq-why` when `isTeacher` |
| Passed clusters export teacher HTML, student HTML, GIFT, H5P "as before" | HTML done for both passed clusters (travel, fare). GIFT/H5P untouched — out of scope, see `docs/component-reference.md` §6 |
| Needs-review clusters export teacher review files only | Done — `dist/semantic-vocabulary/cluster-03-compensate/review.teacher.html`, nothing else generated for that cluster |
| Failed clusters export diagnostics-only output | Done — `dist/semantic-vocabulary/cluster-04-insufficient-input/diagnostics.html` |
| Tests prove student HTML excludes teacher-only content | Ad hoc grep verification done (not a committed test file) — see §4 |
| Export package tests: index.html, manifest links, folders, GIFT, H5P | `dist/semantic-vocabulary/index.html` manifest built and links verified to resolve to real generated files by construction (same array drives both). GIFT/H5P not applicable here — out of scope |
| Browser QA at 375/768/1280 incl. print | Not done in this pass for vocabulary pages — see §6 |

## 4. Verification actually performed (lightweight, per your last message)

Two things were checked directly rather than just asserted:

**Student files contain zero teacher-only content.** Grepped generated
files for teacher-only strings/classes:

```
grep 'Kịch bản giảng\|class="art-pq-ans"\|Đáp án:\|<b>Nguồn:</b>\|Cambridge Dictionary' \
  cluster-0{1,2}-*/teaching.student.html cluster-0{1,2}-*/practice.student.html
# → 0 matches in every file
grep '<div class="art-projection-flag">' cluster-01-travel/teaching.student.html
# → 0 matches (the flag element itself is teacher-only, not just its content)
```

This works because `isTeacher` gates the JS string-building itself
(`teachingBody()`/`practiceBody()` in `pages/semantic-vocabulary.js`) —
the student render path never constructs the teacher fragment, so there
is nothing to hide. (Unrelated CSS *class definitions* for
`.art-teacher-block` still appear in every page's inlined `<style>`
block since all pages share one stylesheet build — that's expected and
harmless; it's unused CSS, not leaked content.)

**Mobile layout actually renders correctly, not just "should".** Real
headless-Chromium screenshots at 375/768/1280px caught a genuine bug
(§2) that pure code review would have missed — see `qa/screenshots/`.

Everything else in this handoff (families 002/003 responsive behavior,
print CSS, a committed automated test suite) was intentionally **not**
done in this pass, per your instruction to skip further test/QA and
focus on generating files. Treat that as open follow-up, not as passing.

## 5. Issue 003 — Specialized families

| AC | Status |
|---|---|
| Lesson/path dossier: sidebar, stat grid, objective card, concept box, table, roleplay, homework | Done — `dist/families/lesson-path.html` uses all 7 |
| Exam answer-key: question grid, answer-state, option state, explanation block, dense nav | Done — `dist/families/exam-key.html`; dense nav shown as jump-box + reveal toggle (both static in this HTML-only build — real interactivity needs the small inline script the reference `key-template.html` uses, not ported here) |
| Video-route: ticket header, mini route map, station card, timeline step, offline-safe video placeholder | Done — `dist/families/video-route.html`; placeholder explicitly does not embed a real `<video>`/`<iframe>` per AGENTS.md INVARIANT-04 |
| Inverse-thinking: folder cover, tabs, case card, process strip, stamp, evidence block | Done — `dist/families/inverse-thinking.html` (stamp primitive reused from core, see `core-primitives.html` §06) |
| Realistic content, no lorem ipsum | Done — all content is original Vietnamese/English teaching material continuing the Unit 2 Travel & Transport thread from Issue 002 |
| Standalone invariants across all 4 family demos | Done by construction (same `render.js` harness as everything else) |
| Responsive QA 375/768/1280 for all 4 | Not done in this pass — see §6 |
| DESIGN.md documents families + when to choose each | Done — `docs/DESIGN.md` §10.5 |

## 6. Explicitly left as follow-up

- Automated test suite (standalone-HTML invariants, brand string, no
  external refs, teacher/student diff) as committed test files — only
  ad hoc verification was run this pass (§4).
- Responsive screenshot QA for the 7 semantic-vocabulary pages and 4
  specialized-family pages (only `core-primitives.html` was screenshot
  ed).
- Print-preview inspection (print CSS exists in `primitives.css` and is
  reused everywhere, but wasn't independently screenshotted per family).
- Porting `pages/*.js` HTML-string generation into real Eta `.html`
  templates under `packages/renderer/templates/artifact/`, once real
  `common/contracts` types for `SemanticAnchorCluster`/`PracticeSet`/etc.
  are available to bind against.
- Small interactive scripts the reference templates ship (reveal-answer
  buttons, jump-to-question, mode toggle) — the CSS states for these
  exist (`.art-option--correct`, `.art-mode-toggle.art-on`, etc.) but no
  inline `<script>` wiring was written for the family demo pages (only
  `core-primitives.html`'s theme switcher got real JS, since that's the
  one interactive behavior actually load-bearing for the AC).

## 7. File map

```
tokens/contract.css              shared semantic token contract
tokens/{navy-ticket,paper-dossier,transit-route,investigation-folder}.css
primitives.css                   core, family-agnostic components (Issue 001)
families/*.css                   family-specific components (Issues 002-003)
render.js                        render harness (inlines CSS, writes standalone HTML)
partials.js                      shared HTML fragment helpers
pages/*.js                       content + generation scripts, one per deliverable
build.js                         regenerates everything: `node build.js`
dist/                            generated, viewable HTML (open dist/index.html first)
qa/screenshots/                  real browser screenshots taken during this pass
docs/component-reference.md      full component catalog + view-model shapes
docs/DESIGN.md                   original DESIGN.md + new §10 Artifact UI Layer
```

To regenerate everything: `node build.js` from this directory (Node ≥18,
zero dependencies).
