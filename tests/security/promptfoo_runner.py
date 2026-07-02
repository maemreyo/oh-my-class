from __future__ import annotations

import subprocess
from pathlib import Path


def run_promptfoo_security_suite(config_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["npx", "promptfoo", "eval", "--config", str(config_path)],
        check=False,
        capture_output=True,
        text=True,
    )
