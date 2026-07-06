from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.contracts.component_strategy_knowledge import (
    DEFAULT_KNOWLEDGE_SOURCE_PATH,
    build_knowledge_index,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_KNOWLEDGE_SOURCE_PATH)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("common/component_strategy_knowledge/knowledge.sqlite"),
    )
    args = parser.parse_args()
    manifest = build_knowledge_index(source_path=args.source, output_path=args.output)
    print(json.dumps(manifest.model_dump(), sort_keys=True))


if __name__ == "__main__":
    main()
