---
title: "Dark-code standing report: auto-surface new zero-caller symbols"
status: ready-for-agent
labels: [governance, dark-code, ci]
created: 2026-07-08
priority: p2
epic: llm-governance-hardening
sequence: 7
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 6. `tests/test_no_dark_runtime_modules.py`'s `REQUIRE_WIRED`/`KNOWN_DARK` ledger (16 entries as of 2026-07-08) is a good self-maintaining mechanism **once a symbol is in it**, but getting a symbol into it is manual — this same grill session found at least 4 more zero-caller symbols (`roadmap_node`, `verify_concept_alignment_with_majority`, `run_coherence_lint`, `complete_non_streaming_chat`) via ad-hoc grep that the ledger didn't already know about.

## What to build

`scripts/find_dark_symbols.py`:
1. Walk `packages/` + `services/` for top-level `def`/`class` definitions (public, i.e. not `_`-prefixed, in non-test files).
2. For each, count references to that symbol's name in any other non-test `.py` file (excluding the defining module itself and `__init__.py` re-exports — matching `test_no_dark_runtime_modules.py`'s own definition of "caller").
3. Diff the zero-reference results against `REQUIRE_WIRED` + `KNOWN_DARK`'s existing symbol list.
4. Print only symbols **not already triaged** in the ledger.

Run periodically (manual invocation or a non-blocking scheduled CI job) — **not** a blocking PR gate, since new code legitimately goes un-wired for a commit or two while a feature is built in steps.

## Acceptance criteria

- [ ] Script runs cleanly against current `packages/`+`services/` tree.
- [ ] First run's output is triaged: each newly-surfaced symbol gets either wired (per this session's `LIC-06`/`LIC-07` for the ones already found) or added to `KNOWN_DARK` with a reason.
- [ ] False-positive rate is acceptable (e.g. doesn't flag things legitimately called only via dynamic dispatch/reflection, dependency injection registries, or `__all__` exports meant for external packages) — if the naive reference-count approach has too many false positives, narrow scope (e.g. only `def`s inside `sub_agents/*/nodes.py` and similarly-shaped "capability module" locations) rather than abandoning the check.

## Blocked by

Nothing.
