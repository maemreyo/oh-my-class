#!/usr/bin/env python3
"""Pinned final certification and evidence manifest for #474."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import platform
import subprocess
import time


@dataclass(frozen=True)
class CertificationStep:
    name: str
    command: tuple[str, ...]


REQUIRED_STEPS = (
    CertificationStep("architecture", ("make", "check-architecture")),
    CertificationStep("content_intelligence", ("make", "check-content-intelligence")),
    CertificationStep("specialist_registry", ("make", "check-specialist-registry")),
    CertificationStep("content_factory_v2", ("make", "check-content-factory-v2")),
    CertificationStep("runtime_resilience", ("make", "check-runtime-resilience")),
    CertificationStep("benchmark_release", ("make", "benchmark-content-release")),
    CertificationStep("effectiveness", ("make", "check-effectiveness-loop")),
    CertificationStep("load_release", ("make", "load-content-factory-release")),
    CertificationStep("schemas", ("make", "check-schemas")),
)


def _run(step: CertificationStep) -> dict[str, object]:
    started = time.monotonic()
    process = subprocess.run(step.command, text=True, capture_output=True)
    elapsed = time.monotonic() - started
    return {
        "name": step.name, "command": list(step.command), "returncode": process.returncode,
        "duration_seconds": round(elapsed, 4),
        "stdout_sha256": hashlib.sha256(process.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(process.stderr.encode()).hexdigest(),
        "stdout_tail": process.stdout[-4000:], "stderr_tail": process.stderr[-4000:],
    }


def _sign(payload: dict[str, object], key: str) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key.encode(), encoded, hashlib.sha256).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="build/content-factory-v2-certification.json")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    key = os.getenv("OMC_CERTIFICATION_SIGNING_KEY") or os.getenv("OMC_BENCHMARK_SIGNING_KEY")
    if not key:
        raise SystemExit("OMC_CERTIFICATION_SIGNING_KEY is required")
    if not args.smoke and (not os.getenv("OMC_LOAD_BASE_URL") or not os.getenv("OMC_LOAD_AUTH_TOKEN")):
        raise SystemExit("release certification requires OMC_LOAD_BASE_URL and OMC_LOAD_AUTH_TOKEN")
    steps = REQUIRED_STEPS[:-2] if args.smoke else REQUIRED_STEPS
    results = []
    for step in steps:
        result = _run(step)
        results.append(result)
        if result["returncode"] != 0:
            break
    passed = len(results) == len(steps) and all(result["returncode"] == 0 for result in results)
    commit = subprocess.run(("git", "rev-parse", "HEAD"), text=True, capture_output=True, check=True).stdout.strip()
    payload: dict[str, object] = {
        "schema_version": "content_factory_v2_certification.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "profile": "smoke" if args.smoke else "release",
        "passed": passed,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "steps": results,
        "rollback": {
            "strategy": "revert certification commit and keep immutable ArtifactDocument/AnswerSet history",
            "data_destructive": False,
            "verified": passed,
        },
    }
    payload["signature"] = _sign(payload, key)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(
        "# Teaching Content Factory V2 Certification\n\n"
        f"- Commit: `{commit}`\n- Profile: `{payload['profile']}`\n- Passed: **{passed}**\n\n"
        + "\n".join(f"- {item['name']}: rc={item['returncode']} ({item['duration_seconds']}s)" for item in results)
        + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
