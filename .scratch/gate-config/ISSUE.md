---
title: "Gate Config: L2 Pattern — Pydantic Settings, Type-safe, Env-overridable"
status: done
labels: [architecture, config]
created: 2026-06-24
priority: p0
report: "02"
---

## What to build

Single `GateConfig` Pydantic Settings class with all gate thresholds and model assignments. Override any value via env vars (`.env` file for local dev). No YAML parsing, no hardcoded constants scattered across files.

**Design decision (grilling Q6-L2):** Pydantic Settings — type-safe, env var override, IDE autocomplete, validates on startup.

## File Structure

```
packages/agents/config/
├── __init__.py
├── gate_config.py       # GateConfig — all quality gate thresholds
└── models.py            # MODELS dict — 9router model assignments
```

## Implementation Spec

### `packages/agents/config/gate_config.py`

```python
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class GateConfig(BaseSettings):
    """Quality gate thresholds and judge configuration.

    All values overridable via environment variables with GATE_ prefix.
    Example: GATE_MIN_SCORE=8.0 in .env raises the pass threshold.
    """
    model_config = SettingsConfigDict(
        env_prefix="GATE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Layer 1: Schema validation
    schema_max_retries: int = 3
    schema_circuit_threshold: int = 3
    schema_circuit_recovery_s: float = 60.0

    # Layer 2-3: Content review
    fact_min_sources: int = 2
    fact_policy: str = "standard"        # "basic" | "standard" | "rigorous"
    age_check_enabled: bool = True
    html_validate_enabled: bool = True
    responsive_check_enabled: bool = False  # Playwright — off for MVP (no headless browser)

    # Layer 4: LLM Judge
    judge_model: str = "f.pro"
    judge_min_score: float = 7.0
    judge_n: int = 1                     # K4: 1 judge MVP, bump to 3 later
    judge_temperature: float = 0.1

    # Layer 5: HITL
    hitl_timeout_hours: int = 24
    hitl_auto_escalate: bool = True
    hitl_max_revisions: int = 3

    # Layer 6: Export readiness
    export_consensus_threshold: float = 0.67   # 2/3 when n_judges=3
    export_min_score: float = 7.0

    # Healing
    max_retries: int = 3                 # total healing attempts before escalate
    healing_base_delay_s: float = 0.5
    healing_max_delay_s: float = 10.0

    # Hard blocks (never disable in production)
    block_missing_doctype: bool = True
    block_external_assets: bool = True
    block_answer_key_leakage: bool = True
    block_missing_brand: bool = True
```

### `packages/agents/config/models.py`

```python
"""9router model assignments for oh-my-class.

Rule: f.pro for heavy reasoning/generation/judgment,
      f.light for fast/cheap/repetitive tasks.

Override via env: MODEL_CONTENT_GENERATION=f.light
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MODEL_", env_file=".env", extra="ignore")

    # Heavy tasks (f.pro)
    blueprint_design: str = "f.pro"
    content_generation: str = "f.pro"
    llm_judge: str = "f.pro"
    fact_verification: str = "f.pro"
    researcher: str = "f.pro"

    # Light tasks (f.light)
    schema_rewrite: str = "f.light"
    summarization: str = "f.light"
    title_generation: str = "f.light"
    content_review_light: str = "f.light"


# Singleton — import this, not ModelConfig()
MODELS = ModelConfig()
```

### `packages/agents/config/__init__.py`

```python
from packages.agents.config.gate_config import GateConfig
from packages.agents.config.models import MODELS

__all__ = ["GateConfig", "MODELS"]
```

### Usage across the codebase

```python
# In any gate node or agent:
from packages.agents.config import GateConfig, MODELS

config = GateConfig()  # reads .env automatically

# Layer 4 judge
if score < config.judge_min_score:
    ...

# Model selection
model = MODELS.llm_judge   # "f.pro"
model = MODELS.summarization  # "f.light"
```

### `.env.example` (commit this, not `.env`)

```dotenv
# Gate thresholds (override defaults)
GATE_JUDGE_MIN_SCORE=7.0
GATE_JUDGE_N=1
GATE_HITL_TIMEOUT_HOURS=24
GATE_MAX_RETRIES=3
GATE_RESPONSIVE_CHECK_ENABLED=false

# Model assignments
MODEL_CONTENT_GENERATION=f.pro
MODEL_LLM_JUDGE=f.pro
MODEL_SUMMARIZATION=f.light

# Telegram notification
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## Tests

```python
# packages/agents/config/tests/test_gate_config.py

def test_defaults_are_sane():
    config = GateConfig()
    assert config.judge_min_score == 7.0
    assert config.judge_n == 1
    assert config.max_retries == 3
    assert config.block_external_assets is True

def test_env_override(monkeypatch):
    monkeypatch.setenv("GATE_JUDGE_MIN_SCORE", "8.5")
    config = GateConfig()
    assert config.judge_min_score == 8.5

def test_model_config_defaults():
    assert MODELS.llm_judge == "f.pro"
    assert MODELS.summarization == "f.light"

def test_hard_blocks_cannot_be_disabled_silently():
    config = GateConfig()
    # Hard blocks default True — production safe
    assert config.block_missing_doctype is True
    assert config.block_answer_key_leakage is True
```

## Acceptance Criteria

- [ ] `GateConfig` Pydantic Settings class with all threshold fields + `GATE_` prefix
- [ ] `ModelConfig` / `MODELS` singleton with all 9router assignments
- [ ] `.env.example` committed with all overridable keys documented
- [ ] `GateConfig()` validates on import — bad env values raise `ValidationError` at startup
- [ ] Every gate node, agent, and middleware imports from `packages.agents.config`, not hardcoded values
- [ ] Tests: defaults, env override, model config

## Dependencies

- Blocked by: nothing (standalone config module)
- Blocks: `quality-gate-nodes`, `healing-orchestrator`, `middleware-full-stack` (all read GateConfig)
- Priority: p0 — should be first thing implemented (all other issues depend on it)
