"""Layer-6 deterministic export-readiness (format requirements), de-stubbed."""

from __future__ import annotations

from packages.quality.layer6_export.export_validator import check_export_readiness


def test_missing_required_type_blocks_that_format() -> None:
    result = check_export_readiness([{"artifact_type": "lesson"}], ["html", "gift"])
    assert not result.passed
    assert "gift" in result.format_issues  # gift requires a quiz artifact
    assert "html" not in result.format_issues  # html requires lesson (present)


def test_all_requirements_met_passes() -> None:
    result = check_export_readiness(
        [{"artifact_type": "lesson"}, {"artifact_type": "quiz"}], ["html", "gift"]
    )
    assert result.passed
    assert result.format_issues == {}


def test_inverse_thinking_lossy_format_blocked() -> None:
    artifacts = [{"artifact_type": "quiz", "metadata": {"methodology": "inverse_thinking"}}]
    result = check_export_readiness(artifacts, ["h5p"])  # h5p unsupported for inverse-thinking
    assert not result.passed
    assert "h5p" in result.format_issues


def test_no_formats_requested_passes() -> None:
    assert check_export_readiness([{"artifact_type": "lesson"}], []).passed
