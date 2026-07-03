"""Tests for ModelAssignments tier-fallback precedence — deterministic, no LLM."""
from __future__ import annotations


# ── Default: all "4omc" when no env vars set ──────────────────────────────────


class TestNoEnvVarsAllDefault:
    def test_strong_tier_defaults_to_4omc(self):
        from packages.agents.config.models import ModelAssignments
        m = ModelAssignments()
        assert m.blueprint_design == "4omc"
        assert m.content_generation == "4omc"
        assert m.llm_judge == "4omc"
        assert m.fact_verification == "4omc"
        assert m.quality_gate == "4omc"

    def test_fast_tier_defaults_to_4omc(self):
        from packages.agents.config.models import ModelAssignments
        m = ModelAssignments()
        assert m.summarization == "4omc"
        assert m.title_generation == "4omc"
        assert m.schema_rewrite == "4omc"

    def test_medium_tier_defaults_to_4omc(self):
        from packages.agents.config.models import ModelAssignments
        m = ModelAssignments()
        assert m.planner == "4omc"
        assert m.researcher == "4omc"
        assert m.content_creator == "4omc"
        assert m.reviewer == "4omc"
        assert m.diagnostician == "4omc"
        assert m.content_review_light == "4omc"


# ── Tier alias: MODEL_STRONG_DEFAULT applies to strong tasks ──────────────────


class TestStrongTierAlias:
    def test_strong_default_overrides_blueprint_design(self, monkeypatch):
        monkeypatch.setenv("MODEL_STRONG_DEFAULT", "gpt-4o")
        from packages.agents.config.models import ModelAssignments
        assert ModelAssignments().blueprint_design == "gpt-4o"

    def test_strong_default_overrides_content_generation(self, monkeypatch):
        monkeypatch.setenv("MODEL_STRONG_DEFAULT", "gpt-4o")
        from packages.agents.config.models import ModelAssignments
        assert ModelAssignments().content_generation == "gpt-4o"

    def test_strong_default_overrides_llm_judge(self, monkeypatch):
        monkeypatch.setenv("MODEL_STRONG_DEFAULT", "gpt-4o")
        from packages.agents.config.models import ModelAssignments
        assert ModelAssignments().llm_judge == "gpt-4o"

    def test_strong_default_overrides_fact_verification(self, monkeypatch):
        monkeypatch.setenv("MODEL_STRONG_DEFAULT", "gpt-4o")
        from packages.agents.config.models import ModelAssignments
        assert ModelAssignments().fact_verification == "gpt-4o"

    def test_strong_default_overrides_quality_gate(self, monkeypatch):
        monkeypatch.setenv("MODEL_STRONG_DEFAULT", "gpt-4o")
        from packages.agents.config.models import ModelAssignments
        assert ModelAssignments().quality_gate == "gpt-4o"

    def test_strong_default_does_not_affect_fast_tier(self, monkeypatch):
        monkeypatch.setenv("MODEL_STRONG_DEFAULT", "gpt-4o")
        from packages.agents.config.models import ModelAssignments
        m = ModelAssignments()
        assert m.summarization == "4omc"
        assert m.title_generation == "4omc"
        assert m.schema_rewrite == "4omc"

    def test_strong_default_does_not_affect_medium_tier(self, monkeypatch):
        monkeypatch.setenv("MODEL_STRONG_DEFAULT", "gpt-4o")
        from packages.agents.config.models import ModelAssignments
        m = ModelAssignments()
        assert m.planner == "4omc"
        assert m.researcher == "4omc"


# ── Tier alias: MODEL_FAST_DEFAULT applies to fast tasks ──────────────────────


class TestFastTierAlias:
    def test_fast_default_overrides_summarization(self, monkeypatch):
        monkeypatch.setenv("MODEL_FAST_DEFAULT", "gpt-3.5-turbo")
        from packages.agents.config.models import ModelAssignments
        assert ModelAssignments().summarization == "gpt-3.5-turbo"

    def test_fast_default_overrides_title_generation(self, monkeypatch):
        monkeypatch.setenv("MODEL_FAST_DEFAULT", "gpt-3.5-turbo")
        from packages.agents.config.models import ModelAssignments
        assert ModelAssignments().title_generation == "gpt-3.5-turbo"

    def test_fast_default_overrides_schema_rewrite(self, monkeypatch):
        monkeypatch.setenv("MODEL_FAST_DEFAULT", "gpt-3.5-turbo")
        from packages.agents.config.models import ModelAssignments
        assert ModelAssignments().schema_rewrite == "gpt-3.5-turbo"

    def test_fast_default_does_not_affect_strong_tier(self, monkeypatch):
        monkeypatch.setenv("MODEL_FAST_DEFAULT", "gpt-3.5-turbo")
        from packages.agents.config.models import ModelAssignments
        m = ModelAssignments()
        assert m.blueprint_design == "4omc"
        assert m.llm_judge == "4omc"


# ── Per-task env wins over tier alias ─────────────────────────────────────────


class TestPerTaskOverride:
    def test_per_task_beats_strong_default(self, monkeypatch):
        monkeypatch.setenv("MODEL_STRONG_DEFAULT", "gpt-4o")
        monkeypatch.setenv("MODEL_LLM_JUDGE", "claude-3-opus")
        from packages.agents.config.models import ModelAssignments
        m = ModelAssignments()
        assert m.llm_judge == "claude-3-opus"
        assert m.blueprint_design == "gpt-4o"  # tier alias applies to others

    def test_per_task_beats_fast_default(self, monkeypatch):
        monkeypatch.setenv("MODEL_FAST_DEFAULT", "gpt-3.5-turbo")
        monkeypatch.setenv("MODEL_SUMMARIZATION", "f.mini")
        from packages.agents.config.models import ModelAssignments
        m = ModelAssignments()
        assert m.summarization == "f.mini"
        assert m.title_generation == "gpt-3.5-turbo"  # tier alias applies

    def test_both_tier_aliases_active_simultaneously(self, monkeypatch):
        monkeypatch.setenv("MODEL_STRONG_DEFAULT", "gpt-4o")
        monkeypatch.setenv("MODEL_FAST_DEFAULT", "gpt-3.5-turbo")
        from packages.agents.config.models import ModelAssignments
        m = ModelAssignments()
        assert m.blueprint_design == "gpt-4o"
        assert m.summarization == "gpt-3.5-turbo"
        assert m.planner == "4omc"  # medium stays at base

    def test_per_task_non_default_beats_tier(self, monkeypatch):
        monkeypatch.setenv("MODEL_STRONG_DEFAULT", "gpt-4o")
        monkeypatch.setenv("MODEL_LLM_JUDGE", "claude-opus-4")
        from packages.agents.config.models import ModelAssignments
        m = ModelAssignments()
        assert m.llm_judge == "claude-opus-4"      # non-4omc per-task wins
        assert m.blueprint_design == "gpt-4o"      # tier alias applies to the rest
