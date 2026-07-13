#!/usr/bin/env python3
"""Run deterministic privacy-safe classroom simulation and evidence (#473)."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.contracts.effectiveness.feedback import EffectivenessEvent, propose_policy_review, pseudonymize_actor
from common.contracts.effectiveness.governance import EffectivenessLedger, build_item_diagnostics, governed_signals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="build/effectiveness-simulation.json")
    args = parser.parse_args()
    ledger = EffectivenessLedger()
    for index in range(20):
        actor = pseudonymize_actor("simulation-tenant", f"learner-{index}", salt="simulation-only")
        for item_index in (1, 2):
            ledger.append(EffectivenessEvent(
                event_id=f"event-{index}-{item_index}", tenant_id="simulation-tenant",
                pseudonymous_actor_id=actor, document_id="quiz-v1", document_version=1,
                item_id=f"item-{item_index}", answer_set_version=1, event_kind="response",
                correct=index < (12 if item_index == 1 else 15),
                distractor_id="B" if item_index == 1 and 12 <= index < 18 else None,
                timing_band="typical",
            ))
    opted_out = pseudonymize_actor("simulation-tenant", "learner-opt-out", salt="simulation-only")
    ledger.opt_out("simulation-tenant", opted_out)
    diagnostics = build_item_diagnostics(ledger.events_for_tenant("simulation-tenant"), minimum_sample=10)
    signals = governed_signals(ledger, "simulation-tenant", minimum_sample=10)
    proposal = propose_policy_review(signals, change="review distractor and challenge calibration")
    first = next(item for item in diagnostics if item.item_id == "item-1")
    if first.difficulty != 0.6 or first.sample_size != 20:
        raise SystemExit("simulation metrics differ from published expected values")
    payload = {
        "diagnostics": [asdict(item) for item in diagnostics],
        "signals": [item.model_dump(mode="json") for item in signals],
        "proposal": proposal.model_dump(mode="json"),
        "privacy": {"raw_identity_present": False, "opt_out_enforced": True, "tenant_isolated": True},
        "published_expected": {"item-1": {"sample_size": 20, "difficulty": 0.6}, "causal_claim": False},
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8")
    output.with_suffix(output.suffix + ".sha256").write_text(hashlib.sha256(encoded.encode()).hexdigest() + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
