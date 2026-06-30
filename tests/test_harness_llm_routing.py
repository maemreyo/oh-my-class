from __future__ import annotations

import pytest

from packages.agents.llm.smoke import SmokeConfig, smoke_probe
from tests.conftest import DeepevalHarnessConfig, RealLlmTestConfig


def test_real_llm_fixture_targets_9router_4omc(real_llm_config: RealLlmTestConfig) -> None:
    assert real_llm_config.base_url == "http://127.0.0.1:20228"
    assert real_llm_config.model == "4omc"


def test_deepeval_harness_is_offline_and_9router_backed(
    deepeval_harness_config: DeepevalHarnessConfig,
) -> None:
    assert deepeval_harness_config.telemetry_disabled is True
    assert deepeval_harness_config.judge_base_url == "http://127.0.0.1:20228"
    assert deepeval_harness_config.judge_model == "4omc"


@pytest.mark.real_llm
async def test_real_llm_fixture_issues_live_9router_call(
    real_llm_config: RealLlmTestConfig,
) -> None:
    result = await smoke_probe(
        SmokeConfig(
            base_url=real_llm_config.base_url,
            model=real_llm_config.model,
            timeout_s=real_llm_config.timeout_s,
        )
    )

    assert result.status == "pass"
    assert result.model_used == "4omc"
