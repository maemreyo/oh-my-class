from __future__ import annotations

import pytest

from packages.quality.layer3_html.html_validator import HTMLValidator
from tests.fixtures.factories import standalone_html_fixture


@pytest.mark.property
class TestHTMLHardBlockProperties:
    @pytest.mark.parametrize(
        ("mutation", "expected_code"),
        [
            (lambda html: html.replace("<!DOCTYPE html>", "", 1), "missing_doctype"),
            (
                lambda html: html.replace(
                    "</head>",
                    '<link rel="stylesheet" href="https://cdn.example.com/app.css"></head>',
                    1,
                ),
                "external_assets",
            ),
            (
                lambda html: html.replace("Student-safe content", "Answer: 42", 1),
                "answer_key_leakage",
            ),
            (
                lambda html: html.replace(
                    "Student-safe content",
                    '<input type="radio" name="unsafe-choice">',
                    1,
                ),
                "native_radio_inputs",
            ),
            (
                lambda html: html.replace(
                    "</body>",
                    '<script src="https://cdn.jsdelivr.net/npm/vue@3"></script></body>',
                    1,
                ),
                "unmanaged_js_runtime",
            ),
            (
                lambda html: html.replace("oh-my-class", "classroom pack", 1),
                "missing_brand_string",
            ),
        ],
    )
    def test_hard_block_fires_for_adversarial_html_mutation(
        self,
        mutation,
        expected_code: str,
    ) -> None:
        html = mutation(standalone_html_fixture())

        result = HTMLValidator().validate(html)

        assert result.passed is False
        assert expected_code in result.hard_block_violations
