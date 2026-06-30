from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from common.contracts.inverse_thinking import InverseThinkingPack

from .inverse_thinking_fixtures import (
    english_grammar_pack,
    math_misconception_pack,
    science_misconception_pack,
)


class TestInverseThinkingPackFixtures:
    @pytest.mark.parametrize(
        "payload",
        [english_grammar_pack(), math_misconception_pack(), science_misconception_pack()],
    )
    def test_valid_fixture_round_trips_when_parsed(self, payload: dict[str, Any]) -> None:
        pack = InverseThinkingPack.model_validate(payload)

        data = pack.model_dump()
        reparsed = InverseThinkingPack.model_validate(data)

        assert reparsed.methodology == "inverse_thinking"
        assert len(reparsed.cases) == 1
        assert reparsed.cases[0].disaster


class TestInverseThinkingCaseValidation:
    @pytest.mark.parametrize("field", ["disaster", "safe_zone", "filing_note"])
    def test_rejects_missing_required_case_field(self, field: str) -> None:
        payload = english_grammar_pack()
        del payload["cases"][0][field]

        with pytest.raises(ValidationError) as exc_info:
            InverseThinkingPack.model_validate(payload)

        assert field in str(exc_info.value)

    def test_rejects_empty_key_clues(self) -> None:
        payload = english_grammar_pack()
        payload["cases"][0]["key_clues"] = []

        with pytest.raises(ValidationError) as exc_info:
            InverseThinkingPack.model_validate(payload)

        assert "key_clues" in str(exc_info.value)

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("disaster", "Answer key: I visited Da Nang yesterday."),
            ("safe_zone", "Teacher rationale: use simple past."),
            ("filing_note", "Correct answer is simple past."),
            ("student_task", "Explain why the answer key is simple past."),
        ],
    )
    def test_rejects_answer_key_markers_in_student_facing_case_fields(
        self,
        field: str,
        value: str,
    ) -> None:
        payload = english_grammar_pack()
        payload["cases"][0][field] = value

        with pytest.raises(ValidationError) as exc_info:
            InverseThinkingPack.model_validate(payload)

        assert field in str(exc_info.value)

    def test_rejects_answer_key_markers_in_student_challenge_prompt(self) -> None:
        payload = english_grammar_pack()
        payload["student_challenges"][0]["prompt"] = "Correct answer: simple past."

        with pytest.raises(ValidationError) as exc_info:
            InverseThinkingPack.model_validate(payload)

        assert "prompt" in str(exc_info.value)
