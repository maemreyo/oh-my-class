from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.methodologies.inverse_thinking import validate_semantics


def test_validate_semantics_names_rule_first_case() -> None:
    payload = english_grammar_pack()
    payload["cases"][0]["disaster"] = "Use simple past with yesterday."

    with pytest.raises(ValidationError) as exc_info:
        validate_semantics(payload)

    assert "case-present-perfect" in str(exc_info.value)
    assert "disaster" in str(exc_info.value)


def test_validate_semantics_names_boundary_less_case() -> None:
    payload = english_grammar_pack()
    payload["cases"][0]["safe_zone"] = "Remember the tense name."

    with pytest.raises(ValidationError) as exc_info:
        validate_semantics(payload)

    assert "case-present-perfect" in str(exc_info.value)
    assert "safe_zone" in str(exc_info.value)
