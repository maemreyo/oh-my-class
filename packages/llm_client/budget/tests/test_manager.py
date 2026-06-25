"""Tests for TokenBudgetManager — soft/hard limits and EMA integration."""
from __future__ import annotations

import logging

from packages.llm_client.budget.config import TokenBudgetConfig
from packages.llm_client.budget.manager import TokenBudgetManager


def test_content_generation_has_no_hard_limit():
    manager = TokenBudgetManager()
    assert manager.get_hard_limit("content_generation") is None


def test_blueprint_design_has_no_hard_limit():
    manager = TokenBudgetManager()
    assert manager.get_hard_limit("blueprint_design") is None


def test_fact_verification_has_no_hard_limit():
    manager = TokenBudgetManager()
    assert manager.get_hard_limit("fact_verification") is None


def test_quality_gate_has_no_hard_limit():
    manager = TokenBudgetManager()
    assert manager.get_hard_limit("quality_gate") is None


def test_summarization_has_hard_limit():
    manager = TokenBudgetManager()
    assert manager.get_hard_limit("summarization") == 800


def test_title_generation_has_hard_limit():
    manager = TokenBudgetManager()
    assert manager.get_hard_limit("title_generation") == 100


def test_schema_rewrite_has_hard_limit():
    manager = TokenBudgetManager()
    assert manager.get_hard_limit("schema_rewrite") == 2000


def test_content_review_light_has_hard_limit():
    manager = TokenBudgetManager()
    assert manager.get_hard_limit("content_review_light") == 1500


def test_hard_limit_tasks_never_return_none():
    manager = TokenBudgetManager()
    for task in ["summarization", "title_generation", "schema_rewrite", "content_review_light"]:
        assert manager.get_hard_limit(task) is not None, f"{task} should have a hard limit"


def test_unknown_task_returns_none_hard_limit():
    manager = TokenBudgetManager()
    assert manager.get_hard_limit("some_unknown_task") is None


def test_soft_limit_uses_config_before_ema_warmup():
    config = TokenBudgetConfig(content_generation_soft_limit=10_000)
    manager = TokenBudgetManager(config)
    assert manager.get_soft_limit("content_generation") == 10_000


def test_soft_limit_uses_ema_after_warmup():
    config = TokenBudgetConfig(ema_min_samples=2, ema_alpha=1.0, ema_headroom=1.5)
    manager = TokenBudgetManager(config)
    manager.record_usage("content_generation", 6000)
    manager.record_usage("content_generation", 6000)
    # EMA = 6000 (alpha=1.0 means always replaces with latest), headroom 1.5x → 9000
    assert manager.get_soft_limit("content_generation") == 9000


def test_soft_limit_fallback_for_unknown_task():
    manager = TokenBudgetManager()
    limit = manager.get_soft_limit("completely_unknown_task")
    assert limit == 8_000  # fallback default


def test_check_soft_limit_within_returns_true():
    manager = TokenBudgetManager(TokenBudgetConfig(content_generation_soft_limit=12_000))
    assert manager.check_soft_limit("content_generation", 10_000) is True


def test_check_soft_limit_exceeded_returns_false(caplog):
    manager = TokenBudgetManager(TokenBudgetConfig(content_generation_soft_limit=5000))
    with caplog.at_level(logging.WARNING):
        result = manager.check_soft_limit("content_generation", 6000)
    assert result is False
    assert "soft limit exceeded" in caplog.text.lower()


def test_check_soft_limit_logs_task_and_overage(caplog):
    manager = TokenBudgetManager(TokenBudgetConfig(content_generation_soft_limit=5000))
    with caplog.at_level(logging.WARNING):
        manager.check_soft_limit("content_generation", 6000)
    # structured logging: task is in the record's extra dict, not the message string
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.task == "content_generation"  # type: ignore[attr-defined]
    assert record.tokens_used == 6000  # type: ignore[attr-defined]


def test_record_usage_updates_ema():
    config = TokenBudgetConfig(ema_min_samples=1)
    manager = TokenBudgetManager(config)
    manager.record_usage("content_generation", 8000)
    # After 1 sample, EMA should be active (min_samples=1)
    ema_limit = manager.get_soft_limit("content_generation")
    # Should be 8000 * headroom (default 1.5) = 12000
    assert ema_limit == int(8000 * 1.5)


def test_summary_returns_all_tracked_tasks():
    manager = TokenBudgetManager()
    result = manager.summary()
    # Should have all soft and hard limit tasks
    expected_tasks = {
        "content_generation", "blueprint_design", "fact_verification", "quality_gate",
        "summarization", "title_generation", "schema_rewrite", "content_review_light",
    }
    assert expected_tasks.issubset(result.keys())


def test_summary_shape():
    manager = TokenBudgetManager()
    result = manager.summary()
    for _task, data in result.items():
        assert "soft_limit" in data
        assert "hard_limit" in data
        assert "ema_samples" in data
        assert "ema_value" in data


def test_summary_ema_samples_zero_before_any_records():
    manager = TokenBudgetManager()
    result = manager.summary()
    for _task, data in result.items():
        assert data["ema_samples"] == 0
        assert data["ema_value"] is None


def test_config_budget_prefix_separate_from_gate_prefix():
    # TokenBudgetConfig uses BUDGET_ prefix, not GATE_
    config = TokenBudgetConfig()
    assert config.model_config["env_prefix"] == "BUDGET_"  # pyright: ignore[reportTypedDictNotRequiredAccess]
