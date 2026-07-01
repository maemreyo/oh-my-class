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


def test_architecture_manifest_path_is_documented() -> None:
    architecture_doc = Path("docs/system/ARCHITECTURE.md").read_text(encoding="utf-8")

    assert str(MANIFEST_PATH.relative_to(Path.cwd())) in architecture_doc
