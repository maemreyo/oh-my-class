# Testing harness and tiers

The project test policy is real infrastructure at the boundary and deterministic
logic inside the boundary.

## Tiers

- Per-commit fast tier: `uv run pytest -m "not real_llm"`
- Nightly/pre-release eval tier: `uv run pytest -m real_llm`

The fast tier may use the real local test database, but must not call an LLM.
The eval tier calls the live 9Router sidecar at `http://127.0.0.1:20228` with
model `4omc`.

## Fixtures

- `real_llm_config`: 9Router base URL/model/timeout for live eval tests. Default timeout is 60s.
- `deepeval_harness_config`: DeepEval judge settings. Confident-AI telemetry is
  disabled with `CONFIDENT_AI_DISABLE_TRACKING=true`; Langfuse is the only
  observability sink when `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` exist.
- `real_db_session`: SQLAlchemy async session bound to a transaction that rolls
  back after each test.

## Fake LLM policy

`FakeListLLM` and `GenericFakeChatModel` are forbidden. Plumbing should be tested
as deterministic logic; quality and evaluator behavior should use `real_llm`.
