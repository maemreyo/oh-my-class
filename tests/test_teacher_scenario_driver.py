from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_driver():
    path = Path("scripts/run_teacher_scenarios.py")
    scripts_dir = str(path.parent.resolve())
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("run_teacher_scenarios", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_teacher_scenarios"] = module
    spec.loader.exec_module(module)
    return module


def test_fixture_driver_records_full_output_matrix(tmp_path: Path) -> None:
    driver = _load_driver()
    config = driver.DriverConfig(
        base_url="http://localhost:8001",
        output_dir=tmp_path,
        fixture=True,
        timeout_seconds=1.0,
    )

    summary = driver.run_fixture(config.output_dir)

    assert summary["matrix_complete"] is True
    assert summary["google_forms"]["status"] == "deferred"
    assert summary["artifact_types"] == [
        "lesson",
        "worksheet",
        "quiz",
        "drill",
        "recap",
        "infographic",
        "flashcard_deck",
        "answer_key",
        "roadmap",
    ]
    scenarios = summary["scenarios"]
    assert len(scenarios) == 4
    for scenario in scenarios:
        artifact_views = scenario["artifact_views"]
        assert set(artifact_views) == set(summary["artifact_types"])
        for views in artifact_views.values():
            assert set(views) == {"student", "teacher"}
        assert set(scenario["exports"]) == {"gift", "h5p", "qti", "flashcard_tsv", "anki_apkg"}
    assert {mode["mode"] for mode in summary["modes"]} == {
        "generate_pack",
        "diagnose_then_generate",
        "plan_unit",
        "vocabulary_batch",
    }
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "index.html").exists()
