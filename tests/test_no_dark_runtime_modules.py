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

Adjacent but distinct convention — ``# BLOCKED-ON:`` markers
--------------------------------------------------------------
``KNOWN_DARK`` is for code with zero callers at all. Some code, though, has a caller
and is correctly implemented, but one specific branch is permanently unreachable
pending external work (a migration, another team's deliverable, etc.) — not dark,
just fail-closed until that dependency lands. Mark that branch with a comment:

    # BLOCKED-ON: <short description> (see <.scratch path or issue id>)

placed directly above the blocked code. This is distinct from ``TODO`` (implies "not
yet written") and from dead code (implies "should be removed") — the code here is
finished and correct, just inert until the referenced work ships. See
``services/gateway/auth/ownership.py``'s ``_check_same_organization`` for a live
example, and ``scripts/list_blocked_on_markers.py`` for a standing report of every
marker in the tree.
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
    # --- real-LLM-integration design interview, 2026-07-08: wired LLMClient.chat/
    # stream/chat_via_streaming_transport to classify provider errors on failure,
    # instead of bare-reraising openai.OpenAIError (see packages/llm_client/client.py).
    ("classify_openai_error", "packages/llm_client/errors.py"),
    # Observability (gap #10 of the same interview): confirms trace_llm_call
    # and its underlying client constructor are genuinely called from the
    # real LLM call path (packages/agents/llm/chat.py), not just defined.
    # This is a live-path-proof in place of a real-Langfuse-server test —
    # no Langfuse instance runs in this dev environment, so this is the cheap
    # guard against the module regressing to genuinely dark/unwired.
    ("trace_llm_call", "packages/agents/observability/tracing.py"),
    ("get_langfuse_client", "packages/agents/observability/langfuse_client.py"),
    # LIC-01 (2026-07-08 grill session): AdaptiveJudge's G-Eval judge, wired
    # into quality_runtime.render_quality as the real content/pedagogy/
    # presentation gate, replacing the LiveReviewerQualityGate heuristic as
    # the sole arbiter (heuristic stays on as a cheap format/PII pre-filter).
    ("reviewer_node", "packages/agents/sub_agents/reviewer/nodes.py"),
    # LIC-06 (2026-07-08 grill session): advisory cross-session coherence lint,
    # wired into unit_planner_node's output (non-blocking — see the module's
    # own docstring: warnings never affect exportability).
    ("run_coherence_lint", "packages/agents/quality/unit_coherence.py"),
    # LIC-08 (2026-07-08 grill session): the real gap behind vocabulary_batch's
    # "stuck at queued" verdict wasn't the orchestrator (already real) or a
    # missing route (contract.mode="vocabulary_batch" already worked via the
    # existing freeform class_info.mode passthrough) — it was that nothing ever
    # called this to populate input_normalization_report before the orchestrator
    # read it. Now wired into _artifact_workflow.
    ("normalize_vocabulary_input", "packages/agents/teaching_pack/vocabulary_input_normalizer.py"),
)

# (symbol, defining_file) — audit-confirmed dark. Promote to REQUIRE_WIRED when wired.
# NOTE: process_clusters_with_concurrency is now wired but only within its own module
# (called by run_vocabulary_batch_orchestrator), which this same-file-blind lint cannot
# see; it is guarded transitively via run_vocabulary_batch_orchestrator in REQUIRE_WIRED.
KNOWN_DARK: tuple[tuple[str, str], ...] = (
    # --- topic-decomposition (units) — parked ---
    ("create_parent_run", "services/gateway/unit_run_store.py"),
    # LIC-06 (2026-07-08 grill session): real, tested (test_concept_alignment.py),
    # but genuinely has no integration point yet — verify_concept_alignment_with_
    # majority needs a question tagged with an assigned KC id/description + sibling
    # KCs; no question/practice generator in the codebase produces that shape today
    # (practice_generator/semantic_anchor.py's items carry no KC association at all;
    # unit_planner assigns KCs at the session level, not per-question). Wiring this
    # in now would mean fabricating fake KC data just to make the call — worse than
    # leaving it documented-dark until a real KC-tagged question generator exists.
    ("verify_concept_alignment_with_majority", "packages/agents/concept_alignment.py"),
    # LIC-07 (2026-07-08 grill session): real LLM branch, zero callers, AND zero
    # references anywhere in services/gateway or docs/ to RoadmapContent/roadmap_node
    # (checked via repo-wide grep) — no route, UI, or documented plan expects this
    # diagnosis-driven personalized roadmap as a distinct feature. content_creator's
    # generic artifact_type="roadmap" already covers the "roadmap" concept for the
    # product surfaces that exist today. Left dark rather than building a new route
    # for a feature nothing currently asks for — a product decision, not a wiring gap.
    ("roadmap_node", "packages/agents/sub_agents/roadmap_agent/nodes.py"),
    # --- resilience / governance / ops — later phases ---
    ("evaluate_model_drift", "packages/agents/config/model_drift.py"),
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
