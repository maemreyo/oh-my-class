---
title: "Document safe-by-default transport principle; add lightweight warning lint"
status: done
labels: [governance, design-principle, llm]
created: 2026-07-08
priority: p3
epic: llm-governance-hardening
sequence: 5
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 4. The concrete instance (`AdaptiveJudge`'s ungoverned default `litellm.acompletion` transport) was already fixed in commit `ec10283` (`packages/quality/layer4_judge/judge_transport.py`'s `default_litellm_transport` now routes through `LLMClient`). As of 2026-07-08 this pattern occurs exactly once in the codebase — full AST-based default-value tracing was judged not worth building for a single instance; do both of the lighter-weight items below instead.

## What to build

1. **Design principle, written down**: "A constructor's pluggable transport/client seam, when it has a default (i.e. the seam is optional), must have a default that is itself safe — routed through `LLMClient`/equivalent governance — not a raw SDK call. 'Nobody overrode it' must never mean 'nobody validated it.'" Add this to wherever the repo's design principles live (e.g. near ADR-032's discussion of the false-green pattern, or a CONTRIBUTING section on LLM call governance).
2. **Lightweight warning lint** (non-blocking): a text/regex-based check, similar in spirit to `tests/test_no_fake_llm.py`, that flags constructor parameters named `*_transport`/`*_client` with a non-`None` default value, for manual review — not a hard CI failure, since a default like `llm_transport: LLMTransport = some_safe_default_function` is fine and shouldn't be banned outright, only surfaced for a human to confirm the default is safe.

## Acceptance criteria

- [x] Principle documented in a discoverable location, cross-referenced from ADR-032 or wherever nearby governance principles already live.
- [x] Warning lint added (can live alongside `tests/test_no_fake_llm.py` or as its own `tests/test_safe_default_transports.py`); confirmed it does not fire on `judge_interface.py`'s now-safe default, and does fire if the old unsafe pattern is reintroduced.

## Blocked by

Nothing.

> Done (2026-07-08): Principle documented as a new "Design principle: safe-by-default
> transport/client seams" section in `docs/adr/032-verification-integrity-and-engineering-
> discipline.md` (no CONTRIBUTING.md exists in this repo; ADR-032 was the best-fitting existing
> home, already covering the false-green pattern this instance is a case of). Added
> `tests/test_safe_default_transports.py`, a regex-based warning lint (same style as
> `tests/test_no_fake_llm.py`) that scans `__init__` signatures under `packages/`+`services/`
> for `*_transport`/`*_client` params with a non-`None` default and emits a `warnings.warn`
> (never asserts, always exits 0). Verified: currently zero offenders (clean pass, no warning);
> temporarily patching `judge_interface.py`'s `llm_transport` default back to the old
> `= default_litellm_transport` pattern makes the lint warn and print the offender, then
> reverted (confirmed via `git diff` — no residual change).
