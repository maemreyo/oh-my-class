from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from common.contracts.grade_band import GradeBand
from common.contracts.subject_capability_pack import (
    SubjectCapabilityPack,
    load_subject_capability_pack,
)

_MATH_PACK_PATH = (
    Path(__file__).resolve().parents[2]
    / "component_strategy_knowledge"
    / "capabilities"
    / "math_capability_pack.json"
)
_SCIENCE_PACK_PATH = (
    Path(__file__).resolve().parents[2]
    / "component_strategy_knowledge"
    / "capabilities"
    / "science_capability_pack.json"
)


def _minimal_pack_kwargs(**overrides: object) -> dict:
    standard = {
        "framework": "CCSS",
        "code": "CCSS.MATH.CONTENT.5.NF.A.1",
        "description_en": "en",
        "description_vi": "vi",
    }
    moet_standard = {**standard, "framework": "MOET_2018", "code": "MOET.X"}
    misconception = {
        "misconception_id": "m1",
        "description_en": "en",
        "description_vi": "vi",
        "guard_strategy": "guard",
    }
    coverage = [
        {
            "grade_band": band.value,
            "artifact_families": ["quiz"],
            "standards": [standard, moet_standard],
            "misconceptions": [misconception],
        }
        for band in GradeBand
    ]
    return {
        "manifest_version": "test-pack.v1",
        "subject": "math",
        "grade_bands": coverage,
        **overrides,
    }


def test_math_capability_pack_json_loads_and_validates() -> None:
    pack = load_subject_capability_pack(_MATH_PACK_PATH)
    assert pack.subject == "math"
    for band in GradeBand:
        coverage = pack.coverage_for(band)
        assert coverage.standards
        assert coverage.misconceptions


def test_science_capability_pack_json_loads_and_validates() -> None:
    pack = load_subject_capability_pack(_SCIENCE_PACK_PATH)
    assert pack.subject == "science"
    for band in GradeBand:
        coverage = pack.coverage_for(band)
        assert coverage.standards
        assert coverage.misconceptions
        assert any(standard.framework == "NGSS" for standard in coverage.standards)


def test_valid_minimal_pack_round_trips() -> None:
    pack = SubjectCapabilityPack.model_validate(_minimal_pack_kwargs())
    assert len(pack.grade_bands) == len(GradeBand)


def test_missing_a_grade_band_is_rejected() -> None:
    kwargs = _minimal_pack_kwargs()
    kwargs["grade_bands"] = kwargs["grade_bands"][:-1]
    with pytest.raises(ValidationError, match="missing_grade_bands"):
        SubjectCapabilityPack.model_validate(kwargs)


def test_duplicate_grade_band_is_rejected() -> None:
    kwargs = _minimal_pack_kwargs()
    kwargs["grade_bands"] = [*kwargs["grade_bands"], kwargs["grade_bands"][0]]
    with pytest.raises(ValidationError, match="missing_grade_bands|duplicate_grade_bands"):
        SubjectCapabilityPack.model_validate(kwargs)


def test_grade_band_missing_a_moet_standard_is_rejected() -> None:
    kwargs = _minimal_pack_kwargs()
    bands = list(kwargs["grade_bands"])
    ccss_only = {**bands[0], "standards": [bands[0]["standards"][0]]}
    kwargs["grade_bands"] = [ccss_only, *bands[1:]]
    with pytest.raises(ValidationError, match="moet_standard_required"):
        SubjectCapabilityPack.model_validate(kwargs)
