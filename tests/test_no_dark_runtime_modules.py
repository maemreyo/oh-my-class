"""Guard against the systemic false-green pattern found in the 2026-07-01 audit.

The audit discovered many real, unit-tested capability modules that are **never
wired into any runtime path**. Their tests pass only because fixtures hand-construct
the intermediate contracts instead of running the prior stage. Per-unit "real DB +
real LLM" does not catch this; only a real-graph end-to-end run (see
``testing/008`` canonical-flow harness) does. This lint is the cheap tripwire that
encodes the exact tell every auditor used: **zero non-test callers**.

Two ledgers, kept honest against the source tree:

- ``REQUIRE_WIRED`` — capabilities that MUST have a non-test runtime caller. The test
  fails if one regresses to dark (silent un-wiring).
- ``KNOWN_DARK`` — capabilities the audit found unwired, quarantined with a reason.
  The test asserts they are STILL dark. When you wire one (e.g. resurrecting the
  ``vocabulary_batch`` chain), this test fails and tells you to promote it into
  ``REQUIRE_WIRED`` — turning the audit into a self-maintaining, executable ledger.

A "caller" = a reference to the symbol in a non-test runtime ``.py`` file **other than
the symbol's own defining module**. ``__init__.py`` re-exports do NOT count as wiring.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (ROOT / "packages", ROOT / "services")

# (symbol, defining_file_relative_to_repo_root)
REQUIRE_WIRED: tuple[tuple[str, str], ...] = (
    # artifact-send-fanout — the one epic wired end-to-end (audit: REAL). Guard it.
    ("coordinate_artifact_fanout", "packages/agents/teaching_pack/artifact_fanout.py"),
    ("generate_one_artifact", "packages/agents/teaching_pack/generate_one_artifact.py"),
    ("run_vocabulary_batch_orchestrator", "packages/agents/teaching_pack/vocabulary_batch_orchestrator.py"),
    ("retrieve_grounding", "packages/agents/grounding/retrieval.py"),
    # --- vocabulary-batch capabilities: WIRED in Phase 2 (were Potemkin at audit) ---
    ("gather_cluster_evidence", "packages/agents/sub_agents/researcher/lexical_evidence.py"),
    ("lexical_grounding_profile", "packages/agents/sub_agents/researcher/lexical_grounding.py"),
    ("synthesize_semantic_anchor_cluster", "packages/agents/sub_agents/content_creator/semantic_anchor_synthesis.py"),
    ("generate_semantic_anchor_practice", "packages/agents/sub_agents/practice_generator/semantic_anchor.py"),
    ("SemanticAnchoringQualityGate", "packages/quality/semantic_anchoring/gate.py"),
)

# (symbol, defining_file) — audit-confirmed dark. Promote to REQUIRE_WIRED when wired.
# NOTE: process_clusters_with_concurrency is now wired but only within its own module
# (called by run_vocabulary_batch_orchestrator), which this same-file-blind lint cannot
# see; it is guarded transitively via run_vocabulary_batch_orchestrator in REQUIRE_WIRED.
KNOWN_DARK: tuple[tuple[str, str], ...] = (
    # --- topic-decomposition (units) — parked ---
    ("create_parent_run", "services/gateway/unit_run_store.py"),
    ("run_coherence_lint", "packages/agents/quality/unit_coherence.py"),
    # --- resilience / governance / ops — later phases ---
    ("evaluate_model_drift", "packages/agents/config/model_drift.py"),
    ("classify_openai_error", "packages/llm_client/errors.py"),
    ("dispatch_slo_alerts", "services/gateway/slo_alerting.py"),
)


def _is_test_path(path: Path) -> bool:
    return (
        path.name.startswith("test_")
        or path.name == "conftest.py"
        or "tests" in path.parts
    )


def _runtime_py_files() -> list[Path]:
    files: list[Path] = []
    for base in RUNTIME_ROOTS:
        files.extend(
            path
            for path in base.rglob("*.py")
            if "__pycache__" not in path.parts and not _is_test_path(path)
        )
    return files


def _has_runtime_caller(symbol: str, defining_file: str) -> bool:
    defining = (ROOT / defining_file).resolve()
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    for path in _runtime_py_files():
        if path.resolve() == defining:
            continue
        if path.name == "__init__.py":  # re-exports are not wiring
            continue
        if pattern.search(path.read_text(encoding="utf-8")):
            return True
    return False


def test_ledger_defining_files_exist() -> None:
    missing = [
        rel
        for _, rel in (*REQUIRE_WIRED, *KNOWN_DARK)
        if not (ROOT / rel).exists()
    ]
    assert not missing, f"ledger points at files that no longer exist — update it: {missing}"


def test_wired_capabilities_have_runtime_callers() -> None:
    regressed = [
        symbol
        for symbol, rel in REQUIRE_WIRED
        if not _has_runtime_caller(symbol, rel)
    ]
    assert not regressed, (
        "capabilities regressed to dark (no non-test runtime caller): "
        f"{regressed}. Either re-wire them, or they became genuinely dead code."
    )


def test_known_dark_capabilities_are_still_dark() -> None:
    newly_wired = [
        symbol
        for symbol, rel in KNOWN_DARK
        if _has_runtime_caller(symbol, rel)
    ]
    assert not newly_wired, (
        "these audit-quarantined capabilities now have a runtime caller — good! "
        "Promote them from KNOWN_DARK to REQUIRE_WIRED so they stay wired: "
        f"{newly_wired}"
    )
