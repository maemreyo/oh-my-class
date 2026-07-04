# [VER-03] Safety-invariant adversarial + mutation testing
Status: TODO
Labels: verification, ci
ADR: 032
Depends on: VER-02

## Context
ADR-032 Decision 3 requires the K-12 safety invariants INVARIANT-05 (student-facing output
must not leak answer keys) and INVARIANT-06 (teacher approval cannot be silently bypassed)
to move from example-based to **property/fuzz + mutation** testing, and makes
`tests/security/` a hard release gate that is never skipped/xfail.

Today the safety tests are behavioral but example-based and thin against adversarial input:

- `tests/security/test_answer_key_leakage.py` parametrizes a fixed list of 7 markers
  (`ANSWER_KEY_MARKERS`, line 9-17) and drives the real `_compliance_gate`
  (`packages/agents/teaching_pack/nodes.py`) — genuinely behavioral, but only covers exact
  literal phrasings. It does not probe spacing variants, unicode look-alikes, HTML-entity
  encoding, or markers split across tags.
- The underlying detector is regex-based and therefore evadable in predictable ways.
  `packages/quality/compliance_policy.py` `ANSWER_LEAK_PATTERNS` (line 44-54) matches
  literal `answer key`, `đáp án:`, `correct answer:` etc. with `re.IGNORECASE` and simple
  `\s*` spacing. It will miss e.g. `a&#110;swer key` (HTML entity), `аnswer` (Cyrillic
  homoglyph), `ans<span>wer</span> key` (split across tags), or wide-space unicode. Nothing
  currently asserts the gate blocks these.
- `tests/security/test_gate_bypass.py` (INVARIANT-06) monkeypatches `interrupt` and asserts
  the approval stage is called before export, plus a static stage-order check
  (`approval_idx < export_idx`, line 70-73). Solid, but example-based; there is no mutation
  check proving that if the gate clause were removed, a test would actually fail.
- `tests/security/test_security_stubs.py` is outright hollow (asserts on self-authored
  literals; mocks the subprocess it "tests") — see VER-01. It must not count as safety
  coverage.
- `hypothesis` is not currently a dependency (no reference in any `pyproject.toml`); it (or
  an equivalent fuzz strategy) must be added for property-based generation. A `property`
  pytest marker already exists in `pyproject.toml`, and CI already runs
  `pytest packages/quality -m property -v`.

This depends on VER-02 because the enforced `tests/security/` tier and the release-gate
wiring are where these adversarial suites live and are guaranteed to run without skip/xfail.

Principle: production-ready, not a patch. Adversarial bar + mutation proof over example
counts; `tests/security/` is a hard release gate, never skipped.

## Scope
- [ ] Add `hypothesis` (or an equivalent property/fuzz generator) as a test dependency and
  wire it into the `property`-marked suites.
- [ ] Build an answer-key adversarial corpus/strategy covering, at minimum: EN and VI
  phrasings (`answer key`, `correct answer:`, `đáp án:`, `đáp án đúng:`); spacing/newline
  variants; unicode homoglyphs (Cyrillic/Greek look-alikes) and full-width/zero-width
  characters; HTML-entity-encoded forms (`&#xNN;`, `&#NN;`, named entities); and markers
  split across HTML tags. Assert `packages/quality/compliance_policy.py` (via
  `answer_key_issues` / `html_hard_blocks` / `_compliance_gate`) blocks ALL of them for
  student artifact types (`STUDENT_ARTIFACT_TYPES`, compliance_policy.py:56-63).
- [ ] Add PII-shape property tests: generate Vietnamese names, emails, phone numbers
  (VN mobile formats), national-ID-like shapes, and assert the PII hard-block path
  (`pii_leakage`) fires on student-facing output. Where the detector is currently weaker
  than the answer-key one, capturing the gaps as failing tests is the point (they define
  the bar the detector must meet).
- [ ] Add student-HTML injection property tests: generate injected `<script>`, external
  `src`/`href`, CDN framework references, native radio inputs, and assert the existing
  hard blocks (`external_assets`, `unmanaged_js_runtime`, `native_radio_inputs`) fire —
  reusing the real `html_hard_blocks` path.
- [ ] Add a lightweight mutation check: a small harness that programmatically disables one
  guard clause at a time in `compliance_policy.py` / the gate (e.g. neutralize
  `answer_key_issues`, or force `teacher_approved=True`) and asserts that at least one
  security test then FAILS. If a mutation survives (all tests still pass), the harness
  fails — proving the tests actually constrain the guard. Keep it targeted (a handful of
  named mutants), not a full mutmut sweep, to stay CI-affordable.
- [ ] Delete or rewrite the hollow `tests/security/test_security_stubs.py` so it drives
  real code (it currently cannot detect any regression).
- [ ] Enforce never-skip: extend the invariant meta-test so `tests/security/` files cannot
  contain `skip(`/`skipif(`/`xfail(` (the existing
  `test_registered_invariant_tests_are_not_skipped_or_xfailed` in
  `tests/test_invariant_coverage.py` already checks registered invariant paths; broaden to
  the whole `tests/security/` tier). Place the adversarial suites in the release gate so a
  slow fuzz run does not gate merges but always runs pre-deploy.

## Acceptance
- Property/fuzz suites for INVARIANT-05 assert the gate blocks answer-key leakage across
  EN/VI phrasings, spacing, unicode homoglyphs, zero/full-width chars, HTML-entity
  encoding, and split-across-tags — with a seeded corpus that includes concrete evasion
  examples the current regex misses.
- PII-shape and student-HTML-injection property suites drive the real `html_hard_blocks` /
  compliance path and assert the corresponding hard-block codes fire.
- The mutation harness: disabling any one targeted guard clause causes at least one
  `tests/security/` test to fail; a surviving mutant fails the harness. Verified by running
  it in-repo and confirming the current (un-mutated) suite is green and each mutant is
  killed.
- `tests/security/test_security_stubs.py` no longer asserts on self-authored literals or
  mocks its own subject; either removed or rewritten to drive production code (checked by
  VER-01's tautology detector).
- No file under `tests/security/` contains `skip(`/`skipif(`/`xfail(`; the meta-test fails
  if one is introduced.
- The suites are registered in the release gate (VER-02) and run there unconditionally.

## References
- ADR-032 (Decision 3: adversarial property/fuzz + mutation; security is a hard release
  gate, never skipped)
- `packages/quality/compliance_policy.py:44-54` (`ANSWER_LEAK_PATTERNS`), `:56-63`
  (`STUDENT_ARTIFACT_TYPES`), `:73-91` (`html_hard_blocks`), `:128-129`
  (`answer_key_issues`), `:132-141` (`check_artifact_answer_key_leakage`)
- `tests/security/test_answer_key_leakage.py:9-17` (fixed marker list to generalize),
  drives `packages/agents/teaching_pack/nodes.py` `_compliance_gate`
- `tests/security/test_gate_bypass.py:70-73` (static stage-order check to back with a
  mutation proof)
- `tests/security/test_security_stubs.py` (hollow tests to remove/rewrite)
- `tests/test_invariant_coverage.py:21-28` (no-skip meta-test to broaden)
- `pyproject.toml` `[tool.pytest.ini_options] markers` (`property` marker already present);
  `.github/workflows/ci.yml` already runs `pytest packages/quality -m property -v`
- `packages/agents/gates/presentation/answer_key_guard.py` (`check_answer_key_leakage`)

## Implementation notes
- Many generated adversarial strings SHOULD be blocked by a correct detector but are NOT
  blocked by the current regex. Decide explicitly per case whether the test hardens the
  detector (regex/normalization upgrade in `compliance_policy.py`) or documents a known gap
  as an xfail — but xfail is forbidden in `tests/security/` per ADR-032, so the honest
  resolution is to strengthen the detector (e.g. HTML-entity-decode and unicode-normalize
  before matching, strip tags for a "flattened text" pass) until the property holds.
- Mutation mechanism: the cheapest robust approach is monkeypatching the guard function to
  a no-op / identity inside the harness and asserting a specific test fails; avoid rewriting
  source files on disk. Enumerate mutants by name so failures are legible.
- Keep the fuzz bounded and deterministic in CI (fixed seed or `hypothesis` profile with a
  capped example count) so the release gate is reproducible.
- Verify the live path: run the mutated suite and confirm each mutant is actually killed by
  a *behavioral* assertion (gate returns blocked), not by an incidental import error.
