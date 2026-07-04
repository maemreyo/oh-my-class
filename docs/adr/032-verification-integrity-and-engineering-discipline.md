# ADR-032: Verification Integrity & Engineering Discipline

## Status

**Proposed** (2026-07-03) — The system's #1 maturity risk (found across 4 review rounds) is
"green but hollow": tests pass while the runtime path is broken (in-memory store behind a Redis
API, capability registry with no caller, revert UI unreachable, escalate route dead,
tautological safety tests). Before scaling or adding elite modules, engineering discipline must
make hollow verification impossible. This ADR sets the CI/testing contract; detail lives in the
`scalability-elite-modules` issue set (VER-*).

## Decision

1. **Live-path proof is a hard CI gate.** Every module/capability must ship a test proving it is
   *actually invoked on the production path*, not merely unit-tested in isolation. Use the
   indexed **CodeGraph** (`.codegraph/`) for deterministic reachability from the compiled graph /
   router handlers. Upgrade `scripts/verify_new_component_tests.py` from filename-substring
   matching (bypassable) to call-graph reachability. Ban tautological tests (registry fed back to
   itself) by review rule + lint.
2. **Test taxonomy is real and tiered.** Enforce placement into
   `tests/{guard,contract,unit,integration,e2e,resilience,security}/`; each tier has a `make`
   target. **Merge gate** (every PR, fast): unit + contract + guard + security + schema parity +
   invariant-coverage meta-test + live-path proof + boundary/lint + new-component-test policy.
   **Release gate** (nightly/pre-deploy, slow): full e2e (FFA-10 driver, real LLM), resilience,
   the ADR-031 full-output matrix. Migrate existing ~453 tests incrementally.
3. **Safety invariants get an adversarial bar.** INVARIANT-05/06 (K-12) move from example-based
   to **property/fuzz + mutation** testing (many answer-key/PII/injection phrasings; a disabled
   guard clause must fail a test). `tests/security/` is a hard release gate, never skipped/xfail.
4. **No defined-but-unemitted signals.** A meta-test asserts every `ObservabilityEventType` in the
   Literal has a live emitter (prevents the round-2/3 recurrence).

## Consequences

- Regressions that drop a live path, an emitter, or a safety case surface at CI, not in prod.
- Slightly slower merges (live-path proof) — justified; advisory is how hollow tests slipped in.
- CodeGraph becomes CI infrastructure, not just a dev aid.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Hard gate + live-path proof (chosen) | Kills green-but-hollow at the source | Slower merges; CodeGraph in CI |
| Advisory warnings only | No merge friction | Exactly how hollow tests shipped before — rejected |
| Coverage-% target only | Simple | Coverage rewards executed lines, not live-path reachability — misses the failure mode |
