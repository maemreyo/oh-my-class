from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from common.contracts.effectiveness.feedback import EffectivenessEvent, pseudonymize_actor
from common.contracts.effectiveness.governance import (
    EffectivenessLedger,
    PrivacyViolation,
    build_item_diagnostics,
    governed_signals,
)


def _event(index: int, *, tenant: str = "tenant-a", item: str = "item-1", version: int = 1, omitted: bool = False):
    return EffectivenessEvent(
        event_id=f"event-{tenant}-{item}-{version}-{index}",
        tenant_id=tenant,
        pseudonymous_actor_id=pseudonymize_actor(tenant, f"student-{index}", salt="test"),
        document_id="doc-1",
        document_version=version,
        item_id=item,
        answer_set_version=version,
        event_kind="omission" if omitted else "response",
        correct=None if omitted else index % 2 == 0,
        omitted=omitted,
        distractor_id="B" if index % 2 else None,
    )


def test_ledger_rejects_raw_actor_identity() -> None:
    ledger = EffectivenessLedger()
    event = _event(1).model_copy(update={"pseudonymous_actor_id": "student@example.com"})
    with pytest.raises(PrivacyViolation):
        ledger.append(event)


def test_opt_out_and_deletion_remove_actor_data() -> None:
    ledger = EffectivenessLedger()
    event = _event(1)
    assert ledger.append(event)
    actor = event.pseudonymous_actor_id
    assert actor is not None
    ledger.opt_out(event.tenant_id, actor)
    assert ledger.events_for_tenant(event.tenant_id) == ()
    assert not ledger.append(event)


def test_tenant_and_version_lineage_never_mix() -> None:
    ledger = EffectivenessLedger()
    for index in range(10):
        ledger.append(_event(index, tenant="tenant-a", version=1))
        ledger.append(_event(index, tenant="tenant-a", version=2))
        ledger.append(_event(index, tenant="tenant-b", version=1))
    signals = governed_signals(ledger, "tenant-a", minimum_sample=10)
    assert len(signals) == 2
    assert {(signal.tenant_id, signal.document_version, signal.answer_set_version) for signal in signals} == {
        ("tenant-a", 1, 1), ("tenant-a", 2, 2)
    }


def test_tiny_cohort_is_withheld() -> None:
    ledger = EffectivenessLedger()
    for index in range(3):
        ledger.append(_event(index))
    signal = governed_signals(ledger, "tenant-a", minimum_sample=10)[0]
    assert signal.status == "insufficient_sample"
    assert signal.metrics == {}


def test_ambiguity_diagnostic_uses_observed_behavior_without_causal_claim() -> None:
    events = tuple(_event(index, omitted=index < 5) for index in range(20))
    diagnostic = build_item_diagnostics(events, minimum_sample=10)[0]
    assert diagnostic.ambiguity_alert
    assert "no causal" in diagnostic.uncertainty_note


def test_effectiveness_simulation_cli_exits_zero_with_privacy_evidence(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[4]
    output = tmp_path / "effectiveness-simulation.json"
    process = subprocess.run(
        [
            sys.executable,
            "scripts/run_effectiveness_simulation.py",
            "--output",
            str(output),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["privacy"] == {
        "raw_identity_present": False,
        "opt_out_enforced": True,
        "tenant_isolated": True,
    }
    assert payload["published_expected"]["item-1"] == {
        "sample_size": 20,
        "difficulty": 0.6,
    }
