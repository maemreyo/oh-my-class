from __future__ import annotations

from pathlib import Path


def test_inverse_thinking_rollout_checklist_documents_required_release_gates() -> None:
    checklist = Path(__file__).with_name("inverse-thinking-rollout-checklist.md").read_text()

    for required in (
        "Dev validation",
        "Staging validation",
        "Beta teacher enablement",
        "Fallback and escalation behavior",
        "Metrics to monitor",
        "No silent downgrade",
    ):
        assert required in checklist
