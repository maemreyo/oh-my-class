from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack, science_misconception_pack
from packages.renderer.inverse_thinking_html import render_release_fixture_html


def test_english_case_file_golden_stays_disaster_first() -> None:
    html = render_release_fixture_html(english_grammar_pack(), artifact_type="lesson")

    assert html.index("I have visited Da Nang yesterday") < html.index("Use simple past")
    assert "This is wrong" not in html


def test_non_detective_science_golden_stays_subject_agnostic() -> None:
    html = render_release_fixture_html(science_misconception_pack(), artifact_type="drill", frame="neutral")

    assert "less current returns" in html
    assert "Current is the same" in html
    assert "frame-neutral" in html
