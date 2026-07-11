from __future__ import annotations

import json
from pathlib import Path

from scripts.check_architecture_truth import check_anatomy_freshness
from scripts.architecture_surfaces import ArchitectureSurfaces, surface_reachability_errors


def test_anatomy_freshness_passes_for_the_committed_trace() -> None:
    assert check_anatomy_freshness() == []


def test_anatomy_freshness_reports_source_drift(tmp_path: Path) -> None:
    module = tmp_path / "packages" / "example"
    module.mkdir(parents=True)
    source = module / "feature.py"
    source.write_text("value = 1\n", encoding="utf-8")

    anatomy = tmp_path / "docs" / "anatomy"
    anatomy.mkdir(parents=True)
    (anatomy / "_modules.json").write_text(
        json.dumps({"example": "packages/example"}), encoding="utf-8"
    )
    (anatomy / "_manifest.json").write_text(
        json.dumps({"modules": {"example": {"hash": "stale", "file_count": 1}}}),
        encoding="utf-8",
    )

    assert check_anatomy_freshness(tmp_path) == [
        "example: source changed at packages/example; refresh docs/anatomy with /anatomy"
    ]


def test_surface_reachability_reports_registered_missing_module(tmp_path: Path) -> None:
    surfaces: ArchitectureSurfaces = {
        "specialists": {"lesson": "packages.agents.teaching_pack.specialists.missing_specialist"},
        "unregistered_specialists": [],
        "renderer_plugins": [],
        "workers": [],
        "stores": [],
        "gate_handlers": [],
    }

    assert surface_reachability_errors(tmp_path, surfaces) == [
        "specialist lesson: registered module is missing: packages.agents.teaching_pack.specialists.missing_specialist"
    ]


def test_surface_reachability_reports_unregistered_specialist(tmp_path: Path) -> None:
    surfaces: ArchitectureSurfaces = {
        "specialists": {},
        "unregistered_specialists": ["packages.agents.teaching_pack.specialists.orphan_specialist"],
        "renderer_plugins": [],
        "workers": [],
        "stores": [],
        "gate_handlers": [],
    }

    assert surface_reachability_errors(tmp_path, surfaces) == [
        "specialist packages.agents.teaching_pack.specialists.orphan_specialist: no registry entry"
    ]


def test_quality_and_llm_client_do_not_import_agents() -> None:
    root = Path(__file__).resolve().parents[1]
    forbidden = "packages.agents"
    sources = [
        *sorted((root / "packages" / "quality").rglob("*.py")),
        *sorted((root / "packages" / "llm_client").rglob("*.py")),
    ]

    offenders = [
        path.relative_to(root).as_posix()
        for path in sources
        if "/tests/" not in path.as_posix()
        if forbidden in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
