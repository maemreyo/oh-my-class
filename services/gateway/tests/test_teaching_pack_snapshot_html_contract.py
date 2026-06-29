from __future__ import annotations

from services.gateway.teaching_pack_snapshot_html import (
    is_standalone_html,
    render_student_preview_html,
)
from services.gateway.teaching_pack_snapshot_validators import remove_answer_keys_from_html


def test_standalone_html_requires_brand_string() -> None:
    html = "<!DOCTYPE html><html><body><main>Student content</main></body></html>"

    assert not is_standalone_html(html)


def test_student_preview_includes_brand_and_omits_question_answers() -> None:
    html = render_student_preview_html({
        "title": "Fractions Quiz",
        "sections": [{
            "title": "Practice",
            "components": [{
                "type": "question_card",
                "text": "Which fraction equals 1/2?",
                "options": {"A": "2/4", "B": "1/3"},
                "answer": "A",
                "explain": "2/4 simplifies to 1/2.",
            }],
        }],
    })

    assert "oh-my-class" in html
    assert "Which fraction equals 1/2?" in html
    assert "2/4" in html
    assert "answer" not in html.lower()
    assert "2/4 simplifies" not in html


def test_answer_key_removal_strips_vietnamese_answer_labels() -> None:
    html = "<!DOCTYPE html><html><body>oh-my-class<p>Đáp án: A</p></body></html>"

    cleaned = remove_answer_keys_from_html(html)

    assert "Đáp án" not in cleaned
