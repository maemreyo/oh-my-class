#!/usr/bin/env python3
"""Run a deterministic privacy-safe classroom observation simulation (#473)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common.contracts.effectiveness.feedback import (
    EffectivenessEvent,
    aggregate_item_observations,
    propose_policy_review,
    pseudonymize_actor,
    signals_from_observations,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="build/effectiveness-simulation.json")
    args = parser.parse_args()
    events = tuple(
        EffectivenessEvent(
            event_id=f"event-{index}", tenant_id="simulation-tenant",
            pseudonymous_actor_id=pseudonymize_actor("simulation-tenant", f"learner-{index}", salt="simulation-only"),
            document_id="quiz-v1", document_version=1, item_id="item-1", answer_set_version=1,
            event_kind="response", correct=index < 12, distractor_id="B" if 12 <= index < 18 else None,
            timing_band="typical",
        )
        for index in range(20)
    )
    observations = aggregate_item_observations(events, minimum_sample=10)
    signals = signals_from_observations(observations)
    proposal = propose_policy_review(signals, change="review item-1 distractor B and challenge calibration")
    observation = observations[0]
    if observation.difficulty != 0.6 or observation.sample_size != 20:
        raise SystemExit("simulation metrics differ from published expected values")
    payload = {
        "observations": [item.model_dump(mode="json") for item in observations],
        "signals": [item.model_dump(mode="json") for item in signals],
        "proposal": proposal.model_dump(mode="json"),
        "published_expected": {"sample_size": 20, "difficulty": 0.6, "causal_claim": False},
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
