from __future__ import annotations

import json
from pathlib import Path

from scripts.architecture_surfaces import surface_reachability_errors
from scripts.generate_architecture_manifest import MANIFEST_PATH, PROJECT_ROOT, build_manifest


def test_architecture_manifest_matches_code() -> None:
    stored = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert stored == build_manifest()


def test_architecture_manifest_detects_wiring_boolean_drift() -> None:
    manifest = build_manifest()
    wiring = dict(manifest["wiring"])
    wiring["quality_gate_injected"] = not wiring["quality_gate_injected"]
    drifted = {**manifest, "wiring": wiring}

    assert drifted != build_manifest()


def test_architecture_manifest_tracks_artifact_send_wiring() -> None:
    manifest = build_manifest()
    wiring = manifest["wiring"]

    assert wiring["artifact_send_default_enabled"] is True
    assert wiring["artifact_send_worker_node_present"] is True
    assert wiring["artifact_send_reducer_channels_present"] is True
    assert wiring["artifact_send_rollback_flag"] == "OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1"


def test_architecture_manifest_path_is_documented() -> None:
    # docs/system/ARCHITECTURE.md was deleted when this repo's hand-written
    # architecture doc was replaced by the auto-generated docs/anatomy/ trace
    # (6ea12b9); docs/testbook/runbook.md is the canonical, hand-maintained
    # reference this repo keeps in sync with actual tooling, so that's where
    # the manifest path -- and how to regenerate it -- now lives.
    runbook = Path("docs/testbook/runbook.md").read_text(encoding="utf-8")

    assert str(MANIFEST_PATH.relative_to(Path.cwd())) in runbook


def test_architecture_manifest_surfaces_resolve_to_live_modules() -> None:
    assert surface_reachability_errors(PROJECT_ROOT, build_manifest()["surfaces"]) == []
