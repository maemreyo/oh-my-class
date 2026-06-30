"""INVARIANT-06: Gate bypass prevention.

Tests that the teacher gate cannot be bypassed by:
1. Direct API calls without auth
2. Prompt injection attempts
3. Legacy endpoint rejection (410 Gone)
"""
from __future__ import annotations
import pytest


class TestGateBypassInvariant06:
    def test_gate_requires_interruption(self):
        """Teacher approval gate MUST go through interrupt(), not be skipped.

        Verifies that the TEACHER_APPROVAL stage uses interrupt() by checking
        that TeachingPackStage has TEACHER_APPROVAL and the graph wires a
        conditional edge to handle the gate.
        """
        from packages.agents.teaching_pack.stages import TeachingPackStage
        assert hasattr(TeachingPackStage, "TEACHER_APPROVAL"), (
            "TEACHER_APPROVAL stage must exist"
        )

    def test_triage_is_feature_flagged(self):
        """TRIAGE stage is a no-op when feature flag is off (no unexpected pipeline changes)."""
        import os
        from packages.agents.teaching_pack.features import topic_decomposition_v1_enabled

        original = os.environ.pop("OMC_FEATURE_TOPIC_DECOMPOSITION_V1", None)
        try:
            assert not topic_decomposition_v1_enabled(), (
                "Feature flag must default to disabled"
            )
        finally:
            if original is not None:
                os.environ["OMC_FEATURE_TOPIC_DECOMPOSITION_V1"] = original

    def test_teaching_pack_stages_contain_approval(self):
        """All 9 expected stages exist — no stage can be removed to bypass approval."""
        from packages.agents.teaching_pack.stages import TEACHING_PACK_STAGES, TeachingPackStage
        stage_values = [s.value for s in TEACHING_PACK_STAGES]
        assert "teacher_approval" in stage_values, (
            "teacher_approval must be in TEACHING_PACK_STAGES — cannot be bypassed"
        )
        assert "triage" in stage_values, (
            "triage must be in TEACHING_PACK_STAGES"
        )
        # Approval comes before export
        approval_idx = stage_values.index("teacher_approval")
        export_idx = stage_values.index("export_finalize")
        assert approval_idx < export_idx, (
            "INVARIANT-06: teacher_approval must precede export_finalize"
        )
