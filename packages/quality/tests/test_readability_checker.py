"""Tests for Flesch-Kincaid readability check (AF4 detective layer)."""
from __future__ import annotations

import pytest


class TestCheckReadability:
    def test_empty_text_passes(self):
        from packages.quality.layer2_content.readability_checker import check_readability
        result = check_readability('', target_grade=6)
        assert result.passed is True
        assert result.fk_grade_level == 0.0

    def test_whitespace_only_text_passes(self):
        from packages.quality.layer2_content.readability_checker import check_readability
        result = check_readability('   ', target_grade=6)
        assert result.passed is True

    def test_simple_text_passes_for_low_grade(self):
        # Short simple words → low FK score → passes for grade 1-3
        from packages.quality.layer2_content.readability_checker import check_readability
        simple = 'The cat sat. The dog ran. We play.'
        result = check_readability(simple, target_grade=2)
        # Should not fail badly — simple text
        assert result.fk_grade_level < 10

    def test_complex_text_fails_for_low_grade(self):
        # Long, polysyllabic words → high FK score → fails for grade 1
        from packages.quality.layer2_content.readability_checker import check_readability
        complex_text = (
            'The photosynthetic process utilises electromagnetic radiation '
            'to catalyse biochemical transformations within chloroplasts. '
            'The mitochondrial oxidative phosphorylation generates adenosine triphosphate molecules.'
        )
        result = check_readability(complex_text, target_grade=1)
        assert result.passed is False
        assert result.deviation > 0   # too complex

    def test_result_has_all_fields(self):
        from packages.quality.layer2_content.readability_checker import check_readability
        result = check_readability('The sky is blue. Birds can fly.', target_grade=3)
        assert hasattr(result, 'fk_grade_level')
        assert hasattr(result, 'target_grade')
        assert hasattr(result, 'deviation')
        assert hasattr(result, 'passed')
        assert hasattr(result, 'warning')
        assert result.target_grade == 3

    def test_deviation_equals_fk_minus_target(self):
        from packages.quality.layer2_content.readability_checker import check_readability
        text = 'The cat sat. The dog ran.'
        result = check_readability(text, target_grade=5)
        expected_dev = round(result.fk_grade_level - 5, 2)
        assert result.deviation == expected_dev

    def test_warning_is_none_when_passed(self):
        from packages.quality.layer2_content.readability_checker import check_readability
        # Use a grade range wide enough to guarantee pass
        text = 'The cat sat on the mat.'
        result = check_readability(text, target_grade=6)   # mid-range; should be within ±2
        if result.passed:
            assert result.warning is None

    def test_warning_is_set_when_failed(self):
        from packages.quality.layer2_content.readability_checker import check_readability
        # Force a failure with very complex text at grade 1
        complex_text = (
            'Electroencephalographic quantification demonstrates neurophysiological '
            'alterations in hippocampal synaptic plasticity mechanisms.'
        )
        result = check_readability(complex_text, target_grade=1)
        if not result.passed:
            assert result.warning is not None
            assert isinstance(result.warning, str)

    def test_max_deviation_constant(self):
        from packages.quality.layer2_content.readability_checker import MAX_DEVIATION
        assert MAX_DEVIATION == 2.0

    def test_passes_when_deviation_exactly_at_limit(self):
        from packages.quality.layer2_content.readability_checker import ReadabilityResult, MAX_DEVIATION
        # Simulate a result at the exact boundary
        result = ReadabilityResult(
            fk_grade_level=8.0,
            target_grade=6,
            deviation=2.0,
            passed=abs(2.0) <= MAX_DEVIATION,
            warning=None,
        )
        assert result.passed is True

    def test_fails_when_deviation_exceeds_limit(self):
        from packages.quality.layer2_content.readability_checker import ReadabilityResult, MAX_DEVIATION
        result = ReadabilityResult(
            fk_grade_level=9.1,
            target_grade=6,
            deviation=3.1,
            passed=abs(3.1) <= MAX_DEVIATION,
            warning='too complex',
        )
        assert result.passed is False
