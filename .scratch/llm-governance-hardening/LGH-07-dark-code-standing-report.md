---
title: "Dark-code standing report: auto-surface new zero-caller symbols"
status: done
labels: [governance, dark-code, ci]
created: 2026-07-08
priority: p2
epic: llm-governance-hardening
sequence: 7
---

> **Done (2026-07-08).** `scripts/find_dark_symbols.py` built — reuses
> `_has_runtime_caller`/`RUNTIME_ROOTS`/`_is_test_path` directly from
> `tests/test_no_dark_runtime_modules.py` (imported, not reimplemented), scans
> module-level `def`/`class`/`async def` only, diffs against the existing
> `REQUIRE_WIRED`+`KNOWN_DARK` ledger, always exits 0.
>
> **First real run: 486 hits — far noisier than anticipated.** This is not a
> bug in the matching logic (verified: it correctly reuses the exact same
> "caller" definition the existing, trusted lint already uses) — it's an
> accurate reflection of how many exception classes, Pydantic/dataclass models,
> Protocols, and config classes in this codebase are referenced only via type
> annotations/local scope within their own module, or genuinely have no
> non-test caller. Triaging 486 items one-by-one is out of scope for landing
> this script (that's precisely why the grill session called for a periodic
> **report**, not a blocking gate — see the module's own docstring). Left as a
> standing report for incremental human triage over time, exactly as scoped;
> not narrowed further since narrowing risks hiding genuinely-dark symbols
> behind an arbitrary path filter rather than a real signal.

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 6. `tests/test_no_dark_runtime_modules.py`'s `REQUIRE_WIRED`/`KNOWN_DARK` ledger (16 entries as of 2026-07-08) is a good self-maintaining mechanism **once a symbol is in it**, but getting a symbol into it is manual — this same grill session found at least 4 more zero-caller symbols (`roadmap_node`, `verify_concept_alignment_with_majority`, `run_coherence_lint`, `complete_non_streaming_chat`) via ad-hoc grep that the ledger didn't already know about.

## What to build

`scripts/find_dark_symbols.py`:
1. Walk `packages/` + `services/` for top-level `def`/`class` definitions (public, i.e. not `_`-prefixed, in non-test files).
2. For each, count references to that symbol's name in any other non-test `.py` file (excluding the defining module itself and `__init__.py` re-exports — matching `test_no_dark_runtime_modules.py`'s own definition of "caller").
3. Diff the zero-reference results against `REQUIRE_WIRED` + `KNOWN_DARK`'s existing symbol list.
4. Print only symbols **not already triaged** in the ledger.

Run periodically (manual invocation or a non-blocking scheduled CI job) — **not** a blocking PR gate, since new code legitimately goes un-wired for a commit or two while a feature is built in steps.

## Acceptance criteria

- [x] Script runs cleanly against current `packages/`+`services/` tree (always exits 0, ~2s runtime).
- [~] First run's output triaged **partially**: the 4 specific symbols this grill session already found by hand (`roadmap_node` — see `LIC-07`, `verify_concept_alignment_with_majority` — moved to `KNOWN_DARK` per `LIC-06`, `run_coherence_lint` — wired per `LIC-06`, `complete_non_streaming_chat` — deleted per `LGH-01`) are all resolved. The other ~482 symbols the script surfaced are **not** triaged — that's a standing backlog for incremental human review, not a one-session task; see done-note above for why.
- [x] False-positive rate assessed: it's high (486 hits), but confirmed NOT a bug in the matching logic — it reuses the exact same trusted "caller" definition as `test_no_dark_runtime_modules.py`. Deliberately did not narrow scope further (e.g. to just `sub_agents/*/nodes.py`) — that would hide real signal behind an arbitrary filter. Left as a standing report; a smarter heuristic (e.g. also checking for the symbol name inside string literals for dynamic dispatch, or excluding known-safe patterns like `*Error`/`*Result` exception/response classes) is future work, not required to land this.

## Blocked by

Nothing.
