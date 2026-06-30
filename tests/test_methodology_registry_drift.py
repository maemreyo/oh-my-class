from __future__ import annotations

from pathlib import Path

import pytest

from scripts.verify_registry_drift import RegistryDriftError, assert_methodology_literals_registered


def test_methodology_literal_drift_guard_reports_file_and_line(tmp_path: Path) -> None:
    fixture = tmp_path / "feature.py"
    fixture.write_text('TAG = "inverse_thinking"\n', encoding="utf-8")

    with pytest.raises(RegistryDriftError) as exc_info:
        assert_methodology_literals_registered(tmp_path)

    assert "feature.py:1:inverse_thinking" in exc_info.value.issues[0]
