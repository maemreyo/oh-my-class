from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

RolloutEnvironment = Literal["development", "staging", "production"]


class InverseThinkingRolloutConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    environment: RolloutEnvironment
    enabled: bool = False

    @property
    def feature_flags(self) -> dict[str, bool]:
        return {"inverse_thinking_v1": self.enabled}


def ensure_inverse_thinking_enabled(config: InverseThinkingRolloutConfig) -> None:
    if not config.enabled:
        msg = f"features.inverse_thinking_v1 is disabled in {config.environment}"
        raise ValueError(msg)
