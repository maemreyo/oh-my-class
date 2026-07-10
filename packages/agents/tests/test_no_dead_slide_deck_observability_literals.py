"""ADR-032 decision 4 meta-test: every `ObservabilityEventType` literal has a
live emitter.

Originally scoped to SDE-11's 5 new literals -- a repo-wide sweep at the time
turned up 4 pre-existing literals ("run_created", "step_started",
"step_completed", "step_failed") with zero production call sites, vestiges of
the decommissioned legacy `/run` graph runtime (see
`services/gateway/tests/test_no_legacy_runtime.py`) that were never migrated
when the pipeline moved to the teaching-pack graph runtime. Those were removed
from `ObservabilityEventType` rather than given a fabricated emitter, and this
test now covers the full Literal so a future addition can't repeat the
"green but hollow" pattern.
"""

from __future__ import annotations

from pathlib import Path
from typing import get_args

from packages.agents.events import ObservabilityEventType

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EVENTS_MODULE = (_REPO_ROOT / "packages" / "agents" / "events.py").resolve()
_PRODUCTION_ROOTS = ("apps", "common", "packages", "services")
_IGNORED_PARTS = frozenset({"__pycache__", "tests", "node_modules", ".next"})


def _production_python_files() -> list[Path]:
    files: list[Path] = []
    for root_name in _PRODUCTION_ROOTS:
        root = _REPO_ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if path.resolve() == _EVENTS_MODULE:
                continue
            if any(part in _IGNORED_PARTS or part.startswith("test_") for part in path.parts):
                continue
            files.append(path)
    return files


def test_every_observability_event_type_has_a_live_emitter() -> None:
    """Fails if any `ObservabilityEventType` literal is declared but no real
    (non-test, non-declaration) source file ever passes it as an
    `event_type` -- ADR-032's "green but hollow" recurrence, caught before
    merge instead of after."""
    declared = set(get_args(ObservabilityEventType.__value__))
    sources = {path: path.read_text(encoding="utf-8") for path in _production_python_files()}
    unemitted = [
        event_type
        for event_type in sorted(declared)
        if not any(f'"{event_type}"' in text for text in sources.values())
    ]
    assert unemitted == [], f"ObservabilityEventType literal(s) with no live emitter: {unemitted}"


if __name__ == "__main__":
    test_every_observability_event_type_has_a_live_emitter()
    print("ok")
