from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM connection config. Env prefix: LLM_"""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    base_url: str = "http://localhost:20228/v1"
    api_key: str = ""
    timeout: float = 300.0
    max_retries: int = 0


# ── Model tier table ──────────────────────────────────────────────────────────
#
# Tier     │ Env alias             │ Tasks
# ─────────┼───────────────────────┼─────────────────────────────────────────────
# strong   │ MODEL_STRONG_DEFAULT  │ blueprint_design, content_generation,
#          │                       │ llm_judge, fact_verification, quality_gate
# medium   │ (always "4omc")       │ lead_agent, planner, researcher,
#          │                       │ content_creator, reviewer, diagnostician,
#          │                       │ content_review_light
# fast     │ MODEL_FAST_DEFAULT    │ summarization, title_generation,
#          │                       │ schema_rewrite
#
# Fallback order: MODEL_<TASK> > MODEL_<TIER>_DEFAULT > "4omc"
# Single-model deployments (no tier env vars set) → "4omc" everywhere.

_STRONG_TIER: frozenset[str] = frozenset({
    "blueprint_design",
    "content_generation",
    "llm_judge",
    "fact_verification",
    "quality_gate",
})
_FAST_TIER: frozenset[str] = frozenset({
    "summarization",
    "title_generation",
    "schema_rewrite",
})


class ModelAssignments(BaseSettings):
    """9Router combo per agent/task. Env prefix: MODEL_

    Tier aliases (set once, apply to all tasks in that tier):
      MODEL_STRONG_DEFAULT  — strong-tier tasks (blueprint, content gen, judges)
      MODEL_FAST_DEFAULT    — fast-tier tasks (summarization, title gen, schema)

    Per-task overrides (MODEL_<TASK>) always take precedence over tier aliases.
    """

    model_config = SettingsConfigDict(
        env_prefix="MODEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Tier aliases — read MODEL_FAST_DEFAULT / MODEL_STRONG_DEFAULT from env
    fast_default: str = "4omc"    # MODEL_FAST_DEFAULT
    strong_default: str = "4omc"  # MODEL_STRONG_DEFAULT

    # medium tier — always "4omc" regardless of tier aliases
    lead_agent: str = "4omc"            # medium
    planner: str = "4omc"               # medium
    researcher: str = "4omc"            # medium
    content_creator: str = "4omc"       # medium
    reviewer: str = "4omc"              # medium
    diagnostician: str = "4omc"         # medium
    content_review_light: str = "4omc"  # medium

    # strong tier — falls back to MODEL_STRONG_DEFAULT
    llm_judge: str = "4omc"             # strong
    fact_verification: str = "4omc"     # strong
    quality_gate: str = "4omc"          # strong
    blueprint_design: str = "4omc"      # strong
    content_generation: str = "4omc"    # strong

    # fast tier — falls back to MODEL_FAST_DEFAULT
    schema_rewrite: str = "4omc"        # fast
    summarization: str = "4omc"         # fast
    title_generation: str = "4omc"      # fast

    @model_validator(mode="after")
    def apply_tier_defaults(self) -> ModelAssignments:
        """Apply tier aliases to fields still at the base default "4omc".

        Precedence: MODEL_<TASK>=<non-4omc> > tier alias > "4omc".

        Tier alias activates only when the field is at the base default "4omc"
        AND the tier alias has been set to a different model. Per-task env vars
        that are explicitly set to a non-4omc value always take precedence.
        """
        strong = self.strong_default.strip() or "4omc"
        fast = self.fast_default.strip() or "4omc"
        for name in self.__class__.model_fields:
            if name in ("fast_default", "strong_default"):
                continue
            current = str(getattr(self, name) or "").strip()
            if current != "4omc":
                continue  # explicit per-task override wins
            if name in _STRONG_TIER and strong != "4omc":
                object.__setattr__(self, name, strong)
            elif name in _FAST_TIER and fast != "4omc":
                object.__setattr__(self, name, fast)
        return self


class MaxTokensConfig(BaseSettings):
    """Per-agent max_tokens budget. Env prefix: MAX_TOKENS_

    Caps total output (thinking + content) so reasoning models
    can't burn unlimited tokens on reasoning.
    """

    model_config = SettingsConfigDict(
        env_prefix="MAX_TOKENS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    planner: int = 8192
    researcher: int = 8192
    content_creator: int = 16384
    diagnostician: int = 4096
    reviewer: int = 4096
    default: int = 8192


class NinerouterConfig(BaseSettings):
    """9Router web tool config. Env prefix: NINEROUTER_"""

    model_config = SettingsConfigDict(
        env_prefix="NINEROUTER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    timeout: float = 30.0
    search_results: int = 5
    min_sources: int = 2
    fetch_limit_basic: int = 2
    fetch_limit_standard: int = 5
    fetch_limit_rigorous: int = 10
    content_truncate: int = 4000


LLM = LLMConfig()
MODELS = ModelAssignments()
MAX_TOKENS = MaxTokensConfig()
NINEROUTER = NinerouterConfig()
