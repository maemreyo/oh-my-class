"""GateConfig — all quality gate thresholds in one Pydantic Settings class.

Every value overridable via environment variable with GATE_ prefix.
Example: GATE_JUDGE_MIN_SCORE=8.0 raises the pass threshold without code changes.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class GateConfig(BaseSettings):
    """Quality gate thresholds and judge configuration."""

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
    fact_policy: str = "standard"          # "basic" | "standard" | "rigorous"
    age_check_enabled: bool = True
    html_validate_enabled: bool = True
    responsive_check_enabled: bool = False  # Playwright — off for MVP

    # Layer 4: LLM Judge
    judge_model: str = "f.pro"
    judge_min_score: float = 7.0
    judge_n: int = 1                       # K4: 1 judge MVP, bump to 3 later
    judge_temperature: float = 0.1

    # Layer 5: HITL
    hitl_timeout_hours: int = 24
    hitl_auto_escalate: bool = True
    hitl_max_revisions: int = 3

    # Layer 6: Export readiness
    export_consensus_threshold: float = 0.67   # 2/3 majority when n_judges=3
    export_min_score: float = 7.0

    # Healing / retry
    max_retries: int = 3
    healing_base_delay_s: float = 0.5
    healing_max_delay_s: float = 10.0

    # Hard blocks — never disable in production
    block_missing_doctype: bool = True
    block_external_assets: bool = True
    block_answer_key_leakage: bool = True
    block_missing_brand: bool = True
