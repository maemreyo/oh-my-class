from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class GateConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GATE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

    schema_max_retries: int = 3
    schema_circuit_threshold: int = 3
    schema_circuit_recovery_s: float = 60.0
    fact_min_sources: int = 2
    fact_policy: str = "standard"
    age_check_enabled: bool = True
    html_validate_enabled: bool = True
    responsive_check_enabled: bool = False
    judge_model: str = "4omc"
    judge_min_score: float = 7.0
    judge_n: int = 3
    judge_temperature: float = 0.1
    hitl_timeout_hours: int = 24
    hitl_auto_escalate: bool = True
    hitl_max_revisions: int = 3
    export_consensus_threshold: float = 0.67
    export_min_score: float = 7.0
    max_retries: int = 3
    healing_base_delay_s: float = 0.5
    healing_max_delay_s: float = 10.0
    preflight_min_length: int = 10
    title_max_length: int = 50
    fast_lane_threshold: float | None = None
    judge_min_words_lesson: int = 180
    judge_min_words_worksheet: int = 90
    judge_min_words_quiz: int = 60
    judge_min_words_drill: int = 80
    judge_min_words_recap: int = 80
    judge_min_words_infographic: int = 60
    judge_min_words_default: int = 80
