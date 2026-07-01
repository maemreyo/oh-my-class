from __future__ import annotations

from packages.agents.config.features import features, reset_features


def test_vocabulary_batch_flag_defaults_off(monkeypatch) -> None:
    monkeypatch.delenv("FEATURE_VOCABULARY_BATCH_V1", raising=False)
    reset_features()

    assert features().vocabulary_batch_v1 is False

    reset_features()


def test_vocabulary_batch_flag_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("FEATURE_VOCABULARY_BATCH_V1", "true")
    reset_features()

    assert features().vocabulary_batch_v1 is True

    reset_features()
