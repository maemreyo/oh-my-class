from __future__ import annotations

import pytest

from packages.agents.inverse_thinking_rollout import (
    InverseThinkingRolloutConfig,
    ensure_inverse_thinking_enabled,
)


def test_rollout_config_can_enable_inverse_thinking_in_dev_and_staging() -> None:
    assert InverseThinkingRolloutConfig(environment="development", enabled=True).enabled is True
    assert InverseThinkingRolloutConfig(environment="staging", enabled=True).enabled is True


def test_disabled_rollout_blocks_inverse_thinking_predictably() -> None:
    config = InverseThinkingRolloutConfig(environment="production", enabled=False)

    with pytest.raises(ValueError, match="inverse_thinking_v1"):
        ensure_inverse_thinking_enabled(config)


def test_enabled_rollout_returns_feature_flag_map() -> None:
    config = InverseThinkingRolloutConfig(environment="staging", enabled=True)

    assert config.feature_flags == {"inverse_thinking_v1": True}
