#!/usr/bin/env python3
"""Drive the real Teaching Content Factory API and assert #130 SLOs."""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.contracts.performance.load_harness import LoadReport, LoadSLO, RunMeasurement, build_load_report

TERMINAL = {"completed", "failed", "cancelled"}


def _read_baseline(path: str | None) -> LoadReport | None:
    if not path:
        return None
    return LoadReport(**json.loads(Path(path).read_text(encoding="utf-8")))


def _write_report(report: LoadReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(report), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(output.suffix + ".sha256").write_text(report.report_hash + "\n", encoding="utf-8")


def _synthetic(profile: str) -> tuple[RunMeasurement, ...]:
    red = profile == "red-control"
    return tuple(
        RunMeasurement(
            run_id=f"synthetic-{index}", latency_seconds=600.0 if red else 20.0 + index,
            succeeded=not red or index > 1, queue_depth_at_submit=20,
            queue_depth_at_finish=25 if red and index == 19 else (0 if index == 19 else 10),
        )
        for index in range(20)
    )


async def _live_measurements(base_url: str, token: str, count: int, timeout: float) -> tuple[tuple[RunMeasurement, ...], float]:
    try:
        import httpx
    except ImportError as exc:
        raise SystemExit("httpx is required for live load execution") from exc
    headers = {"Authorization": f"Bearer {token}"}
    started = time.monotonic()
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), headers=headers, timeout=30.0) as client:
        submissions: list[tuple[str, float]] = []
        for index in range(count):
            response = await client.post(
                "/teaching-packs/runs",
                json={
                    "raw_request": f"Create a concise grade 5 math teaching pack load sample {index}",
                    "class_info": {"grade": 5, "subject": "math", "language": "en"},
                },
                headers={**headers, "Idempotency-Key": f"load-{int(started)}-{index}"},
            )
            response.raise_for_status()
            submissions.append((str(response.json()["run_id"]), time.monotonic()))
        pending = dict(submissions)
        results: list[RunMeasurement] = []
        deadline = time.monotonic() + timeout
        while pending and time.monotonic() < deadline:
            for run_id, submitted_at in tuple(pending.items()):
                response = await client.get(f"/teaching-packs/runs/{run_id}")
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                status = str(payload.get("status"))
                if status in TERMINAL:
                    results.append(RunMeasurement(
                        run_id=run_id,
                        latency_seconds=time.monotonic() - submitted_at,
                        succeeded=status == "completed",
                    ))
                    pending.pop(run_id)
            if pending:
                await asyncio.sleep(1.0)
        for run_id, submitted_at in pending.items():
            results.append(RunMeasurement(run_id, time.monotonic() - submitted_at, False, queue_depth_at_finish=len(pending)))
    return tuple(results), time.monotonic() - started


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("smoke", "release", "red-control"), default="smoke")
    parser.add_argument("--base-url", default=os.getenv("OMC_LOAD_BASE_URL"))
    parser.add_argument("--auth-token", default=os.getenv("OMC_LOAD_AUTH_TOKEN"))
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--baseline")
    parser.add_argument("--output", default="build/content-factory-load-report.json")
    args = parser.parse_args()
    if args.profile == "release" and (not args.base_url or not args.auth_token):
        raise SystemExit("release profile requires OMC_LOAD_BASE_URL and OMC_LOAD_AUTH_TOKEN")
    if args.base_url:
        measurements, elapsed = asyncio.run(_live_measurements(args.base_url, args.auth_token or "", args.count, args.timeout))
    else:
        measurements, elapsed = _synthetic(args.profile), 60.0 if args.profile != "red-control" else 600.0
    report = build_load_report(
        measurements, profile=args.profile, elapsed_seconds=elapsed,
        slo=LoadSLO(), baseline=_read_baseline(args.baseline),
    )
    _write_report(report, Path(args.output))
    print(json.dumps(asdict(report), sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
