"""Pipeline V2 deployment and execution configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

_POLICY_YAML_ERROR: Final = "Invalid Pipeline V2 policy YAML"

if TYPE_CHECKING:
    from pathlib import Path


class PipelineV2Config(BaseSettings):
    """Environment-backed Pipeline V2 runtime configuration."""

    model_config = SettingsConfigDict(
        env_prefix="PIPELINE_V2_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    enabled: bool = True
    require_postgres: bool = True
    default_artifact_parallelism: int = Field(default=2, ge=1, le=8)
    max_run_duration_seconds: int = Field(default=3600, gt=0)
    max_stage_duration_seconds: int = Field(default=900, gt=0)
    max_artifact_attempts: int = Field(default=3, ge=1, le=10)
    max_healing_attempts: int = Field(default=3, ge=0, le=10)
    max_prompt_chars: int = Field(default=120_000, gt=0)
    capture_full_prompt_io: bool = False


class ResearchPolicyConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    default_queries: int = Field(ge=1, le=20)
    default_fetches: int = Field(ge=0, le=20)


class ArtifactPolicyConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    core_types: tuple[str, ...] = Field(min_length=1)


class PipelineV2Policy(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1)
    research: ResearchPolicyConfig
    artifacts: ArtifactPolicyConfig


def load_policy_file(path: Path) -> PipelineV2Policy:
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(_POLICY_YAML_ERROR) from error
    try:
        return PipelineV2Policy.model_validate(raw)
    except ValidationError as error:
        raise ValueError(_POLICY_YAML_ERROR) from error
