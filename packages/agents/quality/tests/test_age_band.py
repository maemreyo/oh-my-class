"""Tests for AgeBand config and grade-aware prompt injection (AF4)."""
from __future__ import annotations

import pytest


class TestAgeBand:
    def test_get_age_band_grade_0_is_early_childhood(self):
        from packages.agents.quality.age_band import get_age_band
        band = get_age_band(0)
        assert band.label == 'Early Childhood'

    def test_get_age_band_grade_1_is_lower_primary(self):
        from packages.agents.quality.age_band import get_age_band
        band = get_age_band(1)
        assert band.label == 'Lower Primary'

    def test_get_age_band_grade_3_is_lower_primary(self):
        from packages.agents.quality.age_band import get_age_band
        band = get_age_band(3)
        assert band.label == 'Lower Primary'

    def test_get_age_band_grade_4_is_upper_primary(self):
        from packages.agents.quality.age_band import get_age_band
        band = get_age_band(4)
        assert band.label == 'Upper Primary'

    def test_get_age_band_grade_6_is_lower_secondary(self):
        from packages.agents.quality.age_band import get_age_band
        band = get_age_band(6)
        assert band.label == 'Lower Secondary'

    def test_get_age_band_grade_10_is_upper_secondary(self):
        from packages.agents.quality.age_band import get_age_band
        band = get_age_band(10)
        assert band.label == 'Upper Secondary'

    def test_get_age_band_grade_13_is_pre_tertiary(self):
        from packages.agents.quality.age_band import get_age_band
        band = get_age_band(13)
        assert band.label == 'Pre-Tertiary'

    def test_get_age_band_above_13_falls_back_to_pre_tertiary(self):
        from packages.agents.quality.age_band import get_age_band
        band = get_age_band(15)
        assert band.label == 'Pre-Tertiary'

    def test_age_bands_has_6_entries(self):
        from packages.agents.quality.age_band import AGE_BANDS
        assert len(AGE_BANDS) == 6

    def test_age_band_is_frozen_immutable(self):
        from packages.agents.quality.age_band import get_age_band
        band = get_age_band(6)
        with pytest.raises((AttributeError, TypeError)):
            band.label = 'hacked'  # type: ignore[misc]


class TestBuildGradePromptSection:
    def test_includes_grade_number(self):
        from packages.agents.quality.age_band import build_grade_prompt_section
        section = build_grade_prompt_section(7)
        assert 'Grade 7' in section

    def test_includes_lexile(self):
        from packages.agents.quality.age_band import build_grade_prompt_section
        section = build_grade_prompt_section(7)
        assert 'Lexile' in section

    def test_includes_bloom_ceiling(self):
        from packages.agents.quality.age_band import build_grade_prompt_section
        section = build_grade_prompt_section(7)
        assert 'analyze' in section   # Grade 7 → Lower Secondary → analyze

    def test_includes_sensitive_topic_tier(self):
        from packages.agents.quality.age_band import build_grade_prompt_section
        section = build_grade_prompt_section(7)
        assert 'Tier' in section

    def test_grade_12_has_evaluate_bloom_ceiling(self):
        from packages.agents.quality.age_band import build_grade_prompt_section
        section = build_grade_prompt_section(12)
        assert 'evaluate' in section

    def test_grade_13_has_create_bloom_ceiling(self):
        from packages.agents.quality.age_band import build_grade_prompt_section
        section = build_grade_prompt_section(13)
        assert 'create' in section
