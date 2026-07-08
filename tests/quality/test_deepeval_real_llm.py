"""DeepEval judge test that genuinely calls 9router — no mocks.

Run nightly with: uv run pytest -m real_llm tests/quality/test_deepeval_real_llm.py

This file exists to hold `test_deepeval_uses_9router_not_openai` (split out of
test_deepeval_config.py on 2026-07-08 — see that file's docstring). It is
currently a placeholder: AdaptiveJudge's default LLM transport
(`packages/quality/layer4_judge/judge_transport.py:default_litellm_transport`)
calls bare `litellm.acompletion(model=..., ...)` with no `base_url`/`api_base`
and a default `model="content-fusion"` that no longer maps to anything (that
name only ever existed in the now-deleted `services/proxy/config.yaml`). There
is no global litellm routing config anywhere in this repo. Writing a genuine
real-9router test here requires first fixing that transport (see the
real-LLM-integration design interview, 2026-07-08) — not attempted in this
file yet to avoid asserting behavior that may not work.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Blocked on fixing AdaptiveJudge's ungoverned litellm transport — see module docstring."
)
