"""DeepEval judge test that genuinely calls 9router — no mocks.

Run nightly with: uv run pytest -m real_llm tests/quality/test_deepeval_real_llm.py

Holds `test_deepeval_uses_9router_not_openai` (split out of test_deepeval_config.py
on 2026-07-08 — see that file's docstring). LIC-09 (2026-07-08): this was a
placeholder skip blocked on "AdaptiveJudge's ungoverned litellm transport" — that
transport was fixed in commit ec10283 (judge_transport.py now routes through
LLMClient/`4omc`), so the skip reason no longer applies. Unskipped and implemented
for real: `LLMClientDeepEvalModel` bridges DeepEval's `DeepEvalBaseLLM` interface to
the same governed `LLMClient` every other real LLM call in this repo uses.
"""
from __future__ import annotations

import json

import pytest
from deepeval.models.base_model import DeepEvalBaseLLM


class LLMClientDeepEvalModel(DeepEvalBaseLLM):
    """DeepEvalBaseLLM implementation routed through LLMClient (not bare litellm/openai)."""

    def __init__(self, model: str) -> None:
        self._model = model

    def load_model(self):
        return self

    def get_model_name(self) -> str:
        return self._model

    def generate(self, prompt: str, schema=None):
        import asyncio
        return asyncio.run(self.a_generate(prompt, schema))

    async def a_generate(self, prompt: str, schema=None):
        from packages.llm_client.client import ChatMessage, LLMClient

        system_prompt = "Respond ONLY with valid JSON. No prose, no markdown fences."
        if schema is not None:
            system_prompt += f"\n\nJSON schema:\n{json.dumps(schema.model_json_schema())}"
        client = LLMClient()
        response = await client.chat(
            model=self._model,
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=prompt),
            ],
            agent="testing",
            task="deepeval_real_llm",
            temperature=0.0,
        )
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1].removeprefix("json").strip()
        data = json.loads(content)
        return schema.model_validate(data) if schema is not None else data


@pytest.mark.real_llm
def test_deepeval_uses_9router_not_openai(deepeval_harness_config) -> None:
    """HallucinationMetric genuinely scores real 9Router (`4omc`) output — no mocks."""
    from deepeval.metrics import HallucinationMetric
    from deepeval.test_case import LLMTestCase

    judge = LLMClientDeepEvalModel(deepeval_harness_config.judge_model)
    metric = HallucinationMetric(model=judge, async_mode=False, include_reason=True)

    score = metric.measure(LLMTestCase(
        input="What do plants use for photosynthesis?",
        actual_output="Plants use sunlight, water, and carbon dioxide to produce energy through photosynthesis.",
        context=["Plants use light energy, water, and carbon dioxide to produce glucose and oxygen."],
    ))

    assert judge.get_model_name() == deepeval_harness_config.judge_model == "4omc"
    assert score == metric.score
    assert 0.0 <= metric.score <= 1.0
