"""Tests for AnswerKeyContent model."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.answer_key import (
    AnswerKeyContent,
    AnswerKeySection,
    AnswerKeyMetadata,
)
from common.contracts.components import QuestionCard, QuestionList


class TestAnswerKeyMetadata:
    def test_defaults(self):
        m = AnswerKeyMetadata(total_questions=40)
        assert m.total_questions == 40
        assert m.groups == {}

    def test_with_groups(self):
        m = AnswerKeyMetadata(
            total_questions=20,
            groups={"a": {"label": "Grammar", "color": "#33508F"}},
        )
        assert "a" in m.groups


class TestAnswerKeySection:
    def test_minimal(self):
        s = AnswerKeySection(id="s1", title="Section I")
        assert s.group == "a"
        assert s.components == []
        assert s.sub is None

    def test_with_components(self):
        qc = QuestionCard(id=1, text="Q?", options={"A": "a"}, answer="A", explain="e")
        s = AnswerKeySection(
            id="s1",
            title="Grammar",
            group="b",
            range="1-10",
            components=[qc],
        )
        assert len(s.components) == 1

    def test_all_optional_fields(self):
        s = AnswerKeySection(
            id="s2",
            title="Vocab",
            sub="Articles",
            range="11-20",
            group="c",
            instruction="Choose the best answer",
            summary="Articles are used before nouns",
        )
        assert s.instruction == "Choose the best answer"
        assert s.summary == "Articles are used before nouns"


class TestAnswerKeyContent:
    def test_minimal(self):
        ak = AnswerKeyContent(title="Test Answer Key")
        assert ak.artifact_type == "answer_key"
        assert ak.theme == "default"
        assert ak.sections == []
        assert ak.metadata.total_questions == 0

    def test_with_sections(self):
        ak = AnswerKeyContent(
            title="HSA Answer Key",
            theme="warm",
            sections=[
                AnswerKeySection(id="s1", title="Grammar"),
                AnswerKeySection(id="s2", title="Vocabulary"),
            ],
        )
        assert len(ak.sections) == 2

    def test_accessibility_default(self):
        ak = AnswerKeyContent(title="Test")
        assert ak.accessibility.get("language") == "vi"

    def test_artifact_type_locked(self):
        ak = AnswerKeyContent(title="Test")
        assert ak.artifact_type == "answer_key"

    def test_invalid_artifact_type_rejected(self):
        with pytest.raises(ValidationError):
            AnswerKeyContent(title="Test", artifact_type="lesson")

    def test_json_roundtrip(self):
        ak = AnswerKeyContent(
            title="Roundtrip Test",
            sections=[AnswerKeySection(id="s1", title="S1")],
        )
        data = ak.model_dump()
        ak2 = AnswerKeyContent.model_validate(data)
        assert ak2.title == ak.title
        assert len(ak2.sections) == 1
