from __future__ import annotations

from packages.agents.config.features import features, reset_features


def test_slide_deck_editor_flag_defaults_off(monkeypatch) -> None:
    monkeypatch.delenv("FEATURE_SLIDE_DECK_EDITOR_V1", raising=False)
    reset_features()

    assert features().slide_deck_editor_v1 is False

    reset_features()


def test_slide_deck_editor_flag_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("FEATURE_SLIDE_DECK_EDITOR_V1", "true")
    reset_features()

    assert features().slide_deck_editor_v1 is True

    reset_features()


def test_slide_deck_ai_rewrite_flag_defaults_off(monkeypatch) -> None:
    monkeypatch.delenv("FEATURE_SLIDE_DECK_AI_REWRITE_V1", raising=False)
    reset_features()

    assert features().slide_deck_ai_rewrite_v1 is False

    reset_features()


def test_slide_deck_ai_rewrite_flag_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("FEATURE_SLIDE_DECK_AI_REWRITE_V1", "true")
    reset_features()

    assert features().slide_deck_ai_rewrite_v1 is True

    reset_features()


def test_the_two_flags_are_independent(monkeypatch) -> None:
    """SDE-10: disabling AI rewrite alone must not affect the editor flag,
    and vice versa -- callers compose the two at the call site."""
    monkeypatch.setenv("FEATURE_SLIDE_DECK_EDITOR_V1", "true")
    monkeypatch.setenv("FEATURE_SLIDE_DECK_AI_REWRITE_V1", "false")
    reset_features()

    assert features().slide_deck_editor_v1 is True
    assert features().slide_deck_ai_rewrite_v1 is False

    reset_features()
