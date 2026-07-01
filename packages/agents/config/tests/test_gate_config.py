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


# ── Pipeline config defaults ──────────────────────────────────────────────────

class TestGateConfigPipelineDefaults:
    def test_preflight_min_length_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().preflight_min_length == 10

    def test_title_max_length_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().title_max_length == 50

    def test_judge_min_words_lesson_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().judge_min_words_lesson == 180

    def test_judge_min_words_quiz_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().judge_min_words_quiz == 60

    def test_judge_min_words_default_default(self):
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().judge_min_words_default == 80

    def test_env_override_preflight_min_length(self, monkeypatch):
        monkeypatch.setenv("GATE_PREFLIGHT_MIN_LENGTH", "20")
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().preflight_min_length == 20

    def test_env_override_title_max_length(self, monkeypatch):
        monkeypatch.setenv("GATE_TITLE_MAX_LENGTH", "100")
        from packages.agents.config.gate_config import GateConfig
        assert GateConfig().title_max_length == 100


# ── ModelConfig / MODELS singleton ────────────────────────────────────────────

class TestModelConfig:
    def test_llm_base_url_uses_local_9router_port(self):
        from packages.agents.config.models import LLMConfig
        assert LLMConfig().base_url == "http://localhost:20228/v1"

    def test_llm_judge_is_f_pro(self):
        from packages.agents.config.models import MODELS
        assert MODELS.llm_judge == "4omc"

    def test_summarization_is_f_pro(self):
        from packages.agents.config.models import MODELS
        assert MODELS.summarization == "4omc"

    def test_content_generation_is_f_pro(self):
        from packages.agents.config.models import MODELS
        assert MODELS.content_generation == "4omc"

    def test_blueprint_design_is_f_pro(self):
        from packages.agents.config.models import MODELS
        assert MODELS.blueprint_design == "4omc"

    def test_schema_rewrite_is_f_pro(self):
        from packages.agents.config.models import MODELS
        assert MODELS.schema_rewrite == "4omc"

    def test_researcher_is_f_pro(self):
        from packages.agents.config.models import MODELS
        assert MODELS.researcher == "4omc"

    def test_lead_agent_is_f_pro(self):
        from packages.agents.config.models import MODELS
        assert MODELS.lead_agent == "4omc"

    def test_env_override_model(self, monkeypatch):
        monkeypatch.setenv("MODEL_CONTENT_GENERATION", "f.light")
        from packages.agents.config.models import ModelAssignments
        assert ModelAssignments().content_generation == "f.light"


# ── Package __init__ ──────────────────────────────────────────────────────────

def test_config_package_exports_gate_config():
    from packages.agents.config import (
        GateConfig,  # noqa: F401  # pyright: ignore[reportUnusedImport]
    )


def test_config_package_exports_models():
    from packages.agents.config import MODELS  # noqa: F401  # pyright: ignore[reportUnusedImport]


# ── NinerouterConfig ─────────────────────────────────────────────────────────

class TestNinerouterConfigDefaults:
    def test_timeout_default(self):
        from packages.agents.config.models import NINEROUTER
        assert NINEROUTER.timeout == 30.0

    def test_search_results_default(self):
        from packages.agents.config.models import NINEROUTER
        assert NINEROUTER.search_results == 5

    def test_min_sources_default(self):
        from packages.agents.config.models import NINEROUTER
        assert NINEROUTER.min_sources == 2

    def test_fetch_limit_standard_default(self):
        from packages.agents.config.models import NINEROUTER
        assert NINEROUTER.fetch_limit_standard == 5

    def test_content_truncate_default(self):
        from packages.agents.config.models import NINEROUTER
        assert NINEROUTER.content_truncate == 4000

    def test_env_override_timeout(self, monkeypatch):
        monkeypatch.setenv("NINEROUTER_TIMEOUT", "60")
        from packages.agents.config.models import NinerouterConfig
        assert NinerouterConfig().timeout == 60.0

    def test_env_override_search_results(self, monkeypatch):
        monkeypatch.setenv("NINEROUTER_SEARCH_RESULTS", "10")
        from packages.agents.config.models import NinerouterConfig
        assert NinerouterConfig().search_results == 10
