from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.contracts.component_strategy_knowledge import (
    default_capability_manifest_path,
    load_knowledge_source,
    validate_knowledge_source,
)


def main() -> None:
    source = load_knowledge_source()
    validate_knowledge_source(source)
    _require_checksum(
        "renderer",
        source.manifest.renderer_capability_checksum,
        default_capability_manifest_path("renderer"),
    )
    _require_checksum(
        "exporter",
        source.manifest.exporter_capability_checksum,
        default_capability_manifest_path("exporter"),
    )


def _require_checksum(kind: str, expected: str, path: Path) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"{kind} capability manifest is stale: expected {expected}, got {actual}")


if __name__ == "__main__":
    main()
