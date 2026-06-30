from __future__ import annotations

from packages.agents.config.model_drift import ModelSnapshot, evaluate_model_drift


def test_regressing_canary_rolls_back_to_last_known_good_content_model() -> None:
    previous = ModelSnapshot("models.v1", {"content_generation": "4omc"})
    current = ModelSnapshot("models.v1", {"content_generation": "f.light"})

    decision = evaluate_model_drift(previous, current, golden_score_delta=-0.05)

    assert decision.changed is True
    assert decision.alert == "model_snapshot_regression"
    assert decision.generation_model == "4omc"
