from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.methodologies.inverse_thinking import normalize_pack


def test_normalize_pack_returns_deterministic_inverse_thinking_pack() -> None:
    payload = english_grammar_pack()
    payload.pop("creative_frame")

    pack = normalize_pack(payload)

    assert pack.methodology == "inverse_thinking"
    assert pack.creative_frame == "auto"
    assert [case.id for case in pack.cases] == ["case-present-perfect"]
    assert pack.teacher_only.answer_key == "She met him last week."
