from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Invariant:
    invariant_id: str
    description: str
    test_path: str


INVARIANT_REGISTRY: Final[tuple[Invariant, ...]] = (
    Invariant(
        invariant_id="INVARIANT-01",
        description="The decommissioned Lead Agent and task stub cannot return to runtime.",
        test_path="tests/test_no_lead_agent.py",
    ),
    Invariant(
        invariant_id="INVARIANT-02",
        description="Layer boundaries prevent packages/common from importing upward.",
        test_path=".github/workflows/ci.yml",
    ),
    Invariant(
        invariant_id="INVARIANT-03",
        description="Legacy graph node functions remain deterministic state transforms.",
        test_path="packages/agents/tests/test_nodes.py",
    ),
    Invariant(
        invariant_id="INVARIANT-04",
        description="Rendered/exported HTML must remain standalone with no external assets.",
        test_path="packages/renderer/__tests__/standalone-assets.test.ts",
    ),
    Invariant(
        invariant_id="INVARIANT-05",
        description="Student-facing output must not leak answer keys.",
        test_path="tests/security/test_answer_key_leakage.py",
    ),
    Invariant(
        invariant_id="INVARIANT-06",
        description="Teacher approval cannot be silently bypassed before export.",
        test_path="tests/security/test_gate_bypass.py",
    ),
    Invariant(
        invariant_id="INVARIANT-07",
        description="LLM calls carry metadata tags for agent, task, run, step, and pipeline.",
        test_path="packages/llm_client/tests/test_tags.py",
    ),
    Invariant(
        invariant_id="INVARIANT-08",
        description="Clarification middleware remains the final active middleware.",
        test_path="tests/test_no_parked_middleware_registered.py",
    ),
    Invariant(
        invariant_id="INVARIANT-09",
        description="Brand tokens are sourced from theme.json design-system files.",
        test_path="tests/test_design_system_contract.py",
    ),
    Invariant(
        invariant_id="INVARIANT-10",
        description="Boundary contracts are canonical common/contracts models.",
        test_path="tests/test_boundary_types_registered.py",
    ),
)
