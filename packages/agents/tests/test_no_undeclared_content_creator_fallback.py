"""#464: "Guard test proving no production code path calls content_creator_node
as an undeclared fallback" (issue's own Required Tests list).

`content_creator_node` (the generic, uncertified LLM-prompt loop) has
exactly two accepted production callers today, both explicitly gated:
- `generate_one_artifact.py`'s fallback branch, reached only when
  `specialist_capability.resolve_specialist_capability` resolves `degraded`
  (which itself requires the explicit `generic_content_creator_fallback_v1`
  feature flag) -- never for an artifact type with a registered specialist.
- `nodes.py::_rollback_artifact_workflow`, the named legacy V1 path used
  only when `OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1` is explicitly set
  (`artifact_send_fanout_v1_enabled()` defaults `True`, i.e. the new
  fanout/specialist-registry path is the default).

A third call site would be a genuine undeclared fallback this test exists to
catch -- it fails if `content_creator_node` is imported/called from any
production file other than these two.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AGENTS_ROOT = PROJECT_ROOT / "packages" / "agents"
SERVICES_ROOT = PROJECT_ROOT / "services"

_ACCEPTED_CALLERS = frozenset({
    "packages/agents/teaching_pack/generate_one_artifact.py",
    "packages/agents/teaching_pack/nodes.py",
})

# The module that defines it, and its own package __init__ -- neither is a
# "caller" in the fallback sense this test cares about.
_EXCLUDED_DEFINITION_FILES = frozenset({
    "packages/agents/sub_agents/content_creator/nodes.py",
    "packages/agents/sub_agents/content_creator/__init__.py",
})


def _references_content_creator_node(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        match node:
            case ast.ImportFrom(names=names) if any(alias.name == "content_creator_node" for alias in names):
                return True
            case ast.Name(id="content_creator_node"):
                return True
    return False


def test_content_creator_node_has_no_undeclared_production_callers() -> None:
    offenders: list[str] = []
    for root in (AGENTS_ROOT, SERVICES_ROOT):
        for path in root.rglob("*.py"):
            relative = str(path.relative_to(PROJECT_ROOT))
            if "/tests/" in f"/{relative}":
                continue
            if relative in _EXCLUDED_DEFINITION_FILES:
                continue
            if not _references_content_creator_node(path):
                continue
            if relative not in _ACCEPTED_CALLERS:
                offenders.append(relative)

    assert offenders == [], (
        "content_creator_node referenced outside the two accepted, explicitly "
        f"gated call sites: {offenders}"
    )


def test_the_two_accepted_callers_still_exist_and_still_reference_it() -> None:
    """The inverse check: if either accepted caller stops referencing
    `content_creator_node` (e.g. removed during a refactor), this list goes
    stale and should shrink -- catches that drift instead of silently
    tolerating dead entries in `_ACCEPTED_CALLERS` forever."""
    for relative in _ACCEPTED_CALLERS:
        path = PROJECT_ROOT / relative
        assert path.exists(), relative
        assert _references_content_creator_node(path), (
            f"{relative} is in _ACCEPTED_CALLERS but no longer references "
            "content_creator_node -- narrow the accepted-callers list"
        )
