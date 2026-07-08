"""Warning lint for the safe-default-transport principle (see ADR-032).

A constructor's pluggable transport/client seam, when it has a default (the
seam is optional), must default to something routed through governance
(LLMClient/equivalent) — never a raw SDK call. "Nobody overrode it" must
never mean "nobody validated it." Concrete instance found and fixed
2026-07-08: ``AdaptiveJudge``'s ``llm_transport`` used to default (via
``or``) to a bare ``litellm.acompletion`` call; see
``packages/quality/layer4_judge/judge_transport.py``.

This is deliberately NOT a hard gate: a default like
``llm_transport: LLMTransport = default_litellm_transport`` is fine and
common — the point is only to surface non-``None`` defaults on
``*_transport``/``*_client`` constructor params for a human to eyeball, not
to ban them. Always exits 0; findings are emitted as warnings, visible in
pytest's warning summary.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (ROOT / "packages", ROOT / "services")

INIT_SIGNATURE_RE = re.compile(r"def __init__\s*\((.*?)\)\s*(?:->\s*[^:]+)?:", re.DOTALL)
TRANSPORT_PARAM_RE = re.compile(r"\b(\w*_(?:transport|client))\s*:\s*[^=,\n]+=\s*([^,\n)]+)")


def _is_test_path(path: Path) -> bool:
    return path.name.startswith("test_") or path.name == "conftest.py" or "tests" in path.parts


def _runtime_py_files() -> list[Path]:
    files: list[Path] = []
    for base in RUNTIME_ROOTS:
        files.extend(
            path
            for path in base.rglob("*.py")
            if "__pycache__" not in path.parts and not _is_test_path(path)
        )
    return files


def test_warn_on_non_none_default_transports() -> None:
    """Surface `__init__` params like `llm_transport: X = raw_call` for review.

    Non-blocking by design (see module docstring) — never asserts, only warns.
    """
    offenders: list[str] = []
    for path in _runtime_py_files():
        text = path.read_text(encoding="utf-8")
        for init_match in INIT_SIGNATURE_RE.finditer(text):
            for name, default in TRANSPORT_PARAM_RE.findall(init_match.group(1)):
                if default.strip() != "None":
                    offenders.append(f"{path.relative_to(ROOT)}: {name} = {default.strip()}")

    if offenders:
        warnings.warn(
            "constructor transport/client params with a non-None default "
            "(confirm each routes through LLMClient/equivalent governance, "
            f"not a raw SDK call — see ADR-032): {offenders}",
            stacklevel=1,
        )
