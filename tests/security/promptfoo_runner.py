from __future__ import annotations

import subprocess
from pathlib import Path


def run_promptfoo_security_suite(
    config_path: Path,
    *,
    output_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    args = ["npx", "promptfoo", "eval", "--config", str(config_path), "--no-cache"]
    if output_path is not None:
        args.extend(["-o", str(output_path)])
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
