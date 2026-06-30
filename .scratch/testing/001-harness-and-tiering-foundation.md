---
title: Test harness & tiering foundation (real DB + real LLM via 9router)
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

The shared foundation every other test issue builds on. Encodes the project policy: **real DB + real LLM, no mocks/fakes**; fake-LLM (`FakeListLLM`/`GenericFakeChatModel`) is **forbidden** — quality is tested with the real LLM, plumbing is tested as deterministic logic separated from the LLM.

- **Tiering**: a `@pytest.mark.real_llm` marker. **Per-commit CI** = deterministic + **real test-DB**, excludes `real_llm`. **Nightly/pre-release** = `real_llm` suite.
- **9router LLM client for tests**: a fixture pointing at 9router `:20228`, model `4omc`, for all `real_llm` tests. No OpenAI default anywhere.
- **Real test-DB fixtures**: ephemeral Postgres (migrated via `make migrate`), per-test isolation/rollback.
- **DeepEval wiring**: DeepEval metrics use a custom LLM judge backed by **9router (`4omc`)**, run in **offline mode** (Confident-AI telemetry off — no data egress); metric results logged to **Langfuse** (single observability source). LangSmith is not used.
- **conftest**: shared fixtures (run/contract/unit factories, real-LLM client, DB session), marker registration, lint that fails on any `FakeListLLM`/`GenericFakeChatModel` import.

## Acceptance criteria

- [ ] `real_llm` marker exists; `uv run pytest -m "not real_llm"` runs the fast tier (real DB, no LLM) and `-m real_llm` runs the eval tier.
- [ ] A real-LLM test fixture targets 9router `:20228` / `4omc`; no test reaches OpenAI or any default provider.
- [ ] Real test-DB fixtures apply migrations and isolate per test; no DB mocks.
- [ ] DeepEval judge is 9router-backed and offline (no telemetry/egress); results are logged to Langfuse.
- [ ] A lint/test fails the build if `FakeListLLM`/`GenericFakeChatModel` (or equivalent LLM fakes) are imported anywhere.
- [ ] Docs state the policy + how to run each tier.

## Detailed test suite

- [ ] `tests/test_harness_tiering.py`: fast-tier collection contains zero `real_llm` tests; eval-tier collection is non-empty.
- [ ] `tests/test_harness_llm_routing.py`: the real-LLM fixture issues a live call to 9router (`4omc`) and returns; no fallback to OpenAI.
- [ ] `tests/test_no_fake_llm.py`: importing a fake LLM anywhere fails the lint check.
- [ ] DB fixture test: a migrated ephemeral DB round-trips a run row and rolls back between tests.
- [ ] Run `uv run pytest -m "not real_llm" -q` and `uv run pytest -m real_llm tests/test_harness_llm_routing.py -q`.

## Blocked by

None - can start immediately
