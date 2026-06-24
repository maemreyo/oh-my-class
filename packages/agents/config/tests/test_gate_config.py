"""Tests for GateConfig and ModelConfig — L2 Pydantic Settings pattern."""

from __future__ import annotations

import pytest


# ── GateConfig ────────────────────────────────────────────────────────────────

class TestGateConfigDefaults:
    def test_judge_min_score_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().judge_min_score == 7.0

    def test_judge_n_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().judge_n == 1

    def test_max_retries_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().max_retries == 3

    def test_hitl_max_revisions_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().hitl_max_revisions == 3

    def test_schema_max_retries_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().schema_max_retries == 3

    def test_fact_min_sources_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().fact_min_sources == 2

    def test_age_check_enabled_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().age_check_enabled is True

    def test_responsive_check_disabled_by_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().responsive_check_enabled is False

    def test_export_min_score_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().export_min_score == 7.0


class TestGateConfigHardBlocks:
    def test_block_external_assets_default_true(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().block_external_assets is True

    def test_block_missing_doctype_default_true(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().block_missing_doctype is True

    def test_block_answer_key_leakage_default_true(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().block_answer_key_leakage is True

    def test_block_missing_brand_default_true(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().block_missing_brand is True


class TestGateConfigEnvOverride:
    def test_env_override_judge_min_score(self, monkeypatch):
        monkeypatch.setenv("GATE_JUDGE_MIN_SCORE", "8.5")
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().judge_min_score == 8.5

    def test_env_override_max_retries(self, monkeypatch):
        monkeypatch.setenv("GATE_MAX_RETRIES", "5")
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().max_retries == 5

    def test_env_override_judge_n(self, monkeypatch):
        monkeypatch.setenv("GATE_JUDGE_N", "3")
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().judge_n == 3

    def test_env_override_responsive_check(self, monkeypatch):
        monkeypatch.setenv("GATE_RESPONSIVE_CHECK_ENABLED", "true")
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().responsive_check_enabled is True

    def test_invalid_env_raises_validation_error(self, monkeypatch):
        from pydantic import ValidationError
        monkeypatch.setenv("GATE_JUDGE_MIN_SCORE", "not_a_number")
        from packages.agents.config.gate_config import GateConfig
        with pytest.raises(ValidationError):
            GateConfig()


# ── ModelConfig / MODELS singleton ────────────────────────────────────────────

class TestModelConfig:
    def test_llm_judge_is_f_pro(self):
        from packages.agents.config.models import MODELS
        assert MODELS.llm_judge == "f.pro"

    def test_summarization_is_f_light(self):
        from packages.agents.config.models import MODELS
        assert MODELS.summarization == "f.light"

    def test_content_generation_is_f_light(self):
        from packages.agents.config.models import MODELS
        assert MODELS.content_generation == "f.light"

    def test_blueprint_design_is_f_light(self):
        from packages.agents.config.models import MODELS
        assert MODELS.blueprint_design == "f.light"

    def test_schema_rewrite_is_f_light(self):
        from packages.agents.config.models import MODELS
        assert MODELS.schema_rewrite == "f.light"

    def test_researcher_is_f_light(self):
        from packages.agents.config.models import MODELS
        assert MODELS.researcher == "f.light"

    def test_lead_agent_is_f_pro(self):
        from packages.agents.config.models import MODELS
        assert MODELS.lead_agent == "f.pro"

    def test_env_override_model(self, monkeypatch):
        monkeypatch.setenv("MODEL_CONTENT_GENERATION", "f.light")
        from packages.agents.config.models import ModelConfig
        assert ModelConfig().content_generation == "f.light"


# ── Package __init__ ──────────────────────────────────────────────────────────

def test_config_package_exports_gate_config():
    from packages.agents.config import GateConfig  # noqa: F401


def test_config_package_exports_models():
    from packages.agents.config import MODELS  # noqa: F401
