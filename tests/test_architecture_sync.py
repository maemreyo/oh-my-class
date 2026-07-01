from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_architecture_manifest import MANIFEST_PATH, build_manifest


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
    architecture_doc = Path("docs/system/ARCHITECTURE.md").read_text(encoding="utf-8")

    assert str(MANIFEST_PATH.relative_to(Path.cwd())) in architecture_doc
