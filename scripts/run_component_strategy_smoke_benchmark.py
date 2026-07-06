from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.contracts.component_strategy_smoke_benchmark import run_component_strategy_smoke_benchmark


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixtures", type=Path, nargs="+")
    parser.add_argument("--p95-latency-ms-threshold", type=float, default=1_000.0)
    args = parser.parse_args()
    report = run_component_strategy_smoke_benchmark(
        fixture_paths=tuple(args.fixtures),
        p95_latency_ms_threshold=args.p95_latency_ms_threshold,
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
