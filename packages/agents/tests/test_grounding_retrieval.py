from __future__ import annotations

from packages.agents.grounding import retrieve_grounding


def test_retrieve_grounding_returns_vn_math_norms_when_grade_five_fractions() -> None:
    result = retrieve_grounding(topic="Phân số", grade="Lớp 5", subject="Toán", locale="vi-VN")

    assert result.grounding_status == "grounded"
    assert result.curriculum == "GDPT-2018"
    assert result.topic_norm is not None
    assert result.topic_norm.lesson_count_min == 4
    assert result.topic_norm.lesson_count_max == 6
    assert result.topic_norm.session_minutes_default == 40
    assert result.topic_norm.bloom_distribution["remember"] == 0.4


def test_retrieve_grounding_returns_ungrounded_when_subject_grade_unknown() -> None:
    result = retrieve_grounding(topic="Fractions", grade="Grade 99", subject="alchemy", locale="en-US")

    assert result.grounding_status == "ungrounded"
    assert result.topic_norm is None
    assert result.age_band is None


def test_retrieve_grounding_returns_age_band_when_grade_matches_primary_band() -> None:
    result = retrieve_grounding(topic="Số thập phân", grade="Lớp 5", subject="Toán", locale="vi-VN")

    assert result.age_band is not None
    assert result.age_band.stage == "primary"
    assert result.age_band.attention_minutes_min == 15
    assert result.age_band.attention_minutes_max == 20


def test_retrieve_grounding_resolves_session_defaults_when_primary_and_secondary() -> None:
    primary = retrieve_grounding(topic="Phân số", grade="Lớp 5", subject="Toán", locale="vi-VN")
    secondary = retrieve_grounding(topic="Hàm số bậc nhất", grade="Lớp 9", subject="Toán", locale="vi-VN")

    assert primary.topic_norm is not None
    assert primary.topic_norm.session_minutes_min == 35
    assert primary.topic_norm.session_minutes_max == 45
    assert secondary.topic_norm is not None
    assert secondary.topic_norm.session_minutes_default == 45
