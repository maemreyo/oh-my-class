"""Tests for Diagnostician Agent and supporting tools."""

import json
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from common.contracts.diagnostic_report import (
    BloomGap,
    DiagnosticReport,
    KnowledgeGap,
    MisconceptionPattern,
)
from common.contracts.student_response import StudentAnswerItem, StudentResponse

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState
    from packages.agents.sub_agents.diagnostician.state import DiagnosticianState

# ── StudentResponse ────────────────────────────────────────────────────────────

class TestStudentAnswerItem:
    def test_valid_correct_answer(self):
        item = StudentAnswerItem(
            question_id=1,
            student_answer="B",
            correct_answer="B",
            is_correct=True,
        )
        assert item.is_correct is True
        assert item.section is None
        assert item.bloom_level is None

    def test_valid_wrong_answer(self):
        item = StudentAnswerItem(
            question_id="q5",
            student_answer="A",
            correct_answer="C",
            is_correct=False,
            section="grammar",
            bloom_level="apply",
        )
        assert item.student_answer == "A"
        assert item.section == "grammar"

    def test_unanswered_question(self):
        item = StudentAnswerItem(
            question_id=3,
            student_answer=None,
            correct_answer="D",
            is_correct=False,
        )
        assert item.student_answer is None

    def test_string_question_id(self):
        item = StudentAnswerItem(
            question_id="reading-01",
            student_answer="B",
            correct_answer="B",
            is_correct=True,
        )
        assert item.question_id == "reading-01"


class TestStudentResponse:
    def test_minimal_valid(self):
        sr = StudentResponse(
            student_id="student-001",
            wrong_question_ids=[1, 3, 5],
        )
        assert sr.student_id == "student-001"
        assert sr.test_id == "unknown"
        assert sr.answers == []
        assert sr.total_questions == 0
        assert sr.context == {}

    def test_with_answers(self):
        sr = StudentResponse(
            student_id="s1",
            wrong_question_ids=[2],
            answers=[
                StudentAnswerItem(
                    question_id=1, student_answer="A", correct_answer="A", is_correct=True
                ),
                StudentAnswerItem(
                    question_id=2, student_answer="B", correct_answer="C", is_correct=False
                ),
            ],
            total_questions=10,
        )
        assert len(sr.answers) == 2
        assert sr.total_questions == 10

    def test_context_dict(self):
        sr = StudentResponse(
            student_id="s2",
            wrong_question_ids=[],
            context={"personality": "shy", "target_exam": "HSA"},
        )
        assert sr.context["personality"] == "shy"

    def test_model_dump_roundtrip(self):
        sr = StudentResponse(
            student_id="s3",
            wrong_question_ids=[1, 2],
            test_id="test-2026-01",
        )
        dumped = sr.model_dump()
        restored = StudentResponse.model_validate(dumped)
        assert restored.student_id == "s3"
        assert restored.test_id == "test-2026-01"


# ── DiagnosticReport ───────────────────────────────────────────────────────────

class TestKnowledgeGap:
    def test_valid(self):
        gap = KnowledgeGap(
            category="grammar",
            error_count=5,
            error_rate=0.83,
            severity="critical",
            question_ids=[1, 2, 3, 4, 5],
        )
        assert gap.severity == "critical"
        assert len(gap.question_ids) == 5

    def test_empty_question_ids(self):
        gap = KnowledgeGap(
            category="vocabulary",
            error_count=0,
            error_rate=0.0,
            severity="minor",
            question_ids=[],
        )
        assert gap.question_ids == []


class TestBloomGap:
    def test_valid(self):
        gap = BloomGap(
            bloom_level="remember",
            vn_name="Nhận biết",
            error_count=3,
            error_rate=0.6,
        )
        assert gap.bloom_level == "remember"
        assert gap.vn_name == "Nhận biết"

    def test_all_bloom_levels(self):
        for level, vn in [
            ("remember", "Nhận biết"),
            ("understand", "Thông hiểu"),
            ("apply", "Vận dụng"),
            ("analyze", "Phân tích"),
            ("evaluate", "Đánh giá"),
            ("create", "Sáng tạo"),
        ]:
            gap = BloomGap(bloom_level=level, vn_name=vn, error_count=1, error_rate=0.5)  # pyright: ignore[reportArgumentType]
            assert gap.bloom_level == level


class TestMisconceptionPattern:
    def test_valid(self):
        pattern = MisconceptionPattern(
            id="C1",
            group="a",
            title="Formula-only learner",
            description="Applies rules without understanding context",
            question_ids=[1, 5, 9],
        )
        assert pattern.id == "C1"
        assert pattern.group == "a"

    def test_groups_a_through_e(self):
        for g in ["a", "b", "c", "d", "e"]:
            p = MisconceptionPattern(
                id="X1", group=g, title="T", description="D", question_ids=[]  # pyright: ignore[reportArgumentType]
            )
            assert p.group == g


class TestDiagnosticReport:
    def _make_minimal(self, student_id: str = "s1") -> dict[str, Any]:
        return {"student_id": student_id}

    def test_minimal_defaults(self):
        report = DiagnosticReport.model_validate(self._make_minimal())
        assert report.knowledge_gaps == []
        assert report.bloom_gaps == []
        assert report.misconception_patterns == []
        assert report.critical_sections == []
        assert report.overall_error_rate == 0.0
        assert report.recommended_level == "B2"
        assert report.summary == ""

    def test_with_all_fields(self):
        data = {
            "student_id": "s2",
            "knowledge_gaps": [
                {"category": "grammar", "error_count": 5, "error_rate": 0.83,
                 "severity": "critical", "question_ids": [1, 2, 3]}
            ],
            "bloom_gaps": [
                {"bloom_level": "apply", "vn_name": "Vận dụng", "error_count": 3, "error_rate": 0.6}
            ],
            "misconception_patterns": [
                {"id": "C1", "group": "a", "title": "Rule over meaning",
                 "description": "Memorises rules without context", "question_ids": [1, 5]}
            ],
            "critical_sections": ["grammar"],
            "overall_error_rate": 0.65,
            "recommended_level": "B1",
            "summary": "Học sinh cần tập trung vào ngữ pháp cơ bản.",
        }
        report = DiagnosticReport.model_validate(data)
        assert len(report.knowledge_gaps) == 1
        assert report.recommended_level == "B1"
        assert "ngữ pháp" in report.summary

    def test_model_dump_roundtrip(self):
        report = DiagnosticReport(
            student_id="s3",
            overall_error_rate=0.4,
            recommended_level="B2",
        )
        dumped = report.model_dump()
        restored = DiagnosticReport.model_validate(dumped)
        assert restored.student_id == "s3"

    def test_exported_from_contracts(self):
        from common.contracts import DiagnosticReport as DiagnosticReportAlias
        assert DiagnosticReportAlias is DiagnosticReport

    def test_rejects_invalid_recommended_level(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            DiagnosticReport(student_id="s1", recommended_level="A0")  # pyright: ignore[reportArgumentType]

    def test_rejects_out_of_range_error_rate(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            DiagnosticReport(student_id="s1", overall_error_rate=1.5)

    def test_rejects_negative_error_rate(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            DiagnosticReport(student_id="s1", overall_error_rate=-0.1)


class TestKnowledgeGapLiterals:
    def test_rejects_invalid_severity(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            KnowledgeGap(
                category="grammar", error_count=1, error_rate=0.5,
                severity="severe", question_ids=[],  # pyright: ignore[reportArgumentType]
            )

    def test_rejects_out_of_range_error_rate(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            KnowledgeGap(
                category="grammar", error_count=1, error_rate=1.5,
                severity="critical", question_ids=[],
            )


class TestBloomGapLiterals:
    def test_rejects_invalid_bloom_level(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            BloomGap(bloom_level="synthesize", vn_name="Tổng hợp", error_count=1, error_rate=0.5)  # pyright: ignore[reportArgumentType]

    def test_rejects_out_of_range_error_rate(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            BloomGap(bloom_level="apply", vn_name="Vận dụng", error_count=1, error_rate=2.0)


class TestMisconceptionPatternLiterals:
    def test_rejects_invalid_group(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            MisconceptionPattern(id="C1", group="z", title="T", description="D", question_ids=[])  # pyright: ignore[reportArgumentType]

    def test_accepts_all_valid_groups(self):
        for g in ["a", "b", "c", "d", "e"]:
            p = MisconceptionPattern(id="C1", group=g, title="T", description="D", question_ids=[])  # pyright: ignore[reportArgumentType]
            assert p.group == g


# ── Diagnostician Tools ────────────────────────────────────────────────────────

class TestBloomTaxonomyLookup:
    def test_valid_level_remember(self):
        from packages.agents.sub_agents.diagnostician.tools import bloom_taxonomy_lookup

        result = bloom_taxonomy_lookup("remember")
        assert result["bloom_level"] == "remember"
        assert result["vn_name"] == "Nhận biết"
        assert "typical_verbs" in result

    def test_all_six_levels(self):
        from packages.agents.sub_agents.diagnostician.tools import bloom_taxonomy_lookup

        for level in ["remember", "understand", "apply", "analyze", "evaluate", "create"]:
            result = bloom_taxonomy_lookup(level)
            assert result["bloom_level"] == level
            assert result["vn_name"]  # non-empty

    def test_case_insensitive(self):
        from packages.agents.sub_agents.diagnostician.tools import bloom_taxonomy_lookup

        result = bloom_taxonomy_lookup("APPLY")
        assert result["vn_name"] == "Vận dụng"

    def test_unknown_level_returns_fallback(self):
        from packages.agents.sub_agents.diagnostician.tools import bloom_taxonomy_lookup

        result = bloom_taxonomy_lookup("synthesize")
        assert result["bloom_level"] == "synthesize"
        assert result["typical_verbs"] == []


class TestQuestionTypeClassifier:
    def test_classifies_by_section(self):
        from packages.agents.sub_agents.diagnostician.tools import question_type_classifier

        section_map = {"1": "grammar", "2": "vocabulary", "3": "grammar"}
        result = question_type_classifier([1, 2, 3], section_map)
        assert "grammar" in result
        assert 1 in result["grammar"]
        assert 3 in result["grammar"]
        assert 2 in result["vocabulary"]

    def test_unmapped_questions_go_to_unknown(self):
        from packages.agents.sub_agents.diagnostician.tools import question_type_classifier

        result = question_type_classifier([99], {})
        assert "unknown" in result
        assert 99 in result["unknown"]

    def test_empty_input(self):
        from packages.agents.sub_agents.diagnostician.tools import question_type_classifier

        result = question_type_classifier([], {})
        assert result == {}


# ── Diagnostician Agent node ───────────────────────────────────────────────────

def _make_llm_mock(
    return_value: str | None = None,
    side_effect: Exception | None = None,
) -> AsyncMock:
    if side_effect is not None:
        return AsyncMock(side_effect=side_effect)
    return AsyncMock(return_value=return_value)


VALID_REPORT_JSON = json.dumps({
    "student_id": "s1",
    "knowledge_gaps": [
        {"category": "grammar", "error_count": 3, "error_rate": 0.75,
         "severity": "critical", "question_ids": [1, 2, 3]}
    ],
    "bloom_gaps": [
        {"bloom_level": "apply", "vn_name": "Vận dụng", "error_count": 3, "error_rate": 0.75}
    ],
    "misconception_patterns": [],
    "critical_sections": ["grammar"],
    "overall_error_rate": 0.6,
    "recommended_level": "B2",
    "summary": "Học sinh cần ôn luyện ngữ pháp và từ vựng.",
})

VALID_REPORT_WRAPPED = f"```json\n{VALID_REPORT_JSON}\n```"
VALID_REPORT_GENERIC_FENCE = f"```\n{VALID_REPORT_JSON}\n```"


class TestDiagnosticianNode:
    def _make_state(self, **overrides) -> dict[str, Any]:
        base = {
            "student_responses": {
                "student_id": "s1",
                "wrong_question_ids": [1, 2, 3],
                "total_questions": 5,
                "answers": [],
            },
            "run_id": "test-run-001",
            "current_step": 0,
        }
        base.update(overrides)
        return base

    @pytest.mark.asyncio
    async def test_returns_diagnostic_report(self):
        from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node

        mock_llm = _make_llm_mock(return_value=VALID_REPORT_WRAPPED)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await diagnostician_node(cast("DiagnosticianState", self._make_state()))

        assert "diagnostic_report" in result
        report = DiagnosticReport.model_validate(result["diagnostic_report"])
        assert report.student_id == "s1"

    @pytest.mark.asyncio
    async def test_parses_json_code_fence(self):
        from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node

        mock_llm = _make_llm_mock(return_value=VALID_REPORT_WRAPPED)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await diagnostician_node(cast("DiagnosticianState", self._make_state()))

        assert result["diagnostic_report"]["recommended_level"] == "B2"

    @pytest.mark.asyncio
    async def test_parses_generic_fence(self):
        from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node

        mock_llm = _make_llm_mock(return_value=VALID_REPORT_GENERIC_FENCE)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await diagnostician_node(cast("DiagnosticianState", self._make_state()))

        assert "diagnostic_report" in result

    @pytest.mark.asyncio
    async def test_parses_bare_json(self):
        from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node

        mock_llm = _make_llm_mock(return_value=VALID_REPORT_JSON)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await diagnostician_node(cast("DiagnosticianState", self._make_state()))

        assert "diagnostic_report" in result

    @pytest.mark.asyncio
    async def test_raises_value_error_on_invalid_json(self):
        from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node

        mock_llm = _make_llm_mock(return_value="not json")
        with (
            patch("packages.agents.llm.complete_json_chat", mock_llm),
            pytest.raises(ValueError, match="Invalid JSON"),
        ):
            await diagnostician_node(cast("DiagnosticianState", self._make_state()))

    @pytest.mark.asyncio
    async def test_raises_value_error_on_llm_error(self):
        from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node

        mock_llm = _make_llm_mock(side_effect=RuntimeError("API timeout"))
        with (
            patch("packages.agents.llm.complete_json_chat", mock_llm),
            pytest.raises(ValueError, match="Diagnostician agent failed"),
        ):
            await diagnostician_node(cast("DiagnosticianState", self._make_state()))

    @pytest.mark.asyncio
    async def test_handles_empty_student_responses(self):
        from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node

        mock_llm = _make_llm_mock(return_value=VALID_REPORT_JSON)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await diagnostician_node(cast("DiagnosticianState", self._make_state(student_responses={})))  # noqa: E501

        assert "diagnostic_report" in result


# ── make_diagnostician_agent ───────────────────────────────────────────────────

class TestMakeDiagnosticianAgent:
    def test_returns_compiled_graph(self):
        from packages.agents.sub_agents.diagnostician.agent import make_diagnostician_agent

        agent = make_diagnostician_agent()
        assert agent is not None
        assert hasattr(agent, "ainvoke")

    def test_agent_module_exports(self):
        from packages.agents.sub_agents.diagnostician import (
            diagnostician_graph_node,
            diagnostician_node,
            make_diagnostician_agent,
        )

        assert callable(make_diagnostician_agent)
        assert callable(diagnostician_node)
        assert callable(diagnostician_graph_node)


# ── diagnostician_graph_node (pipeline adapter) ────────────────────────────────

class TestDiagnosticianGraphNode:
    @pytest.mark.asyncio
    async def test_skips_when_no_student_responses(self):
        from packages.agents.sub_agents.diagnostician.agent import diagnostician_graph_node

        result = await diagnostician_graph_node(cast("OhMyClassState", {"student_responses": None}))
        assert result == {}

    @pytest.mark.asyncio
    async def test_skips_when_empty_dict(self):
        from packages.agents.sub_agents.diagnostician.agent import diagnostician_graph_node

        result = await diagnostician_graph_node(cast("OhMyClassState", {"student_responses": {}}))
        assert result == {}

    @pytest.mark.asyncio
    async def test_skips_when_key_absent(self):
        from packages.agents.sub_agents.diagnostician.agent import diagnostician_graph_node

        result = await diagnostician_graph_node(cast("OhMyClassState", {}))
        assert result == {}

    @pytest.mark.asyncio
    async def test_fails_closed_on_llm_error(self):
        """Present data + LLM failure → ValueError propagates (fail closed)."""
        from packages.agents.sub_agents.diagnostician.agent import diagnostician_graph_node

        valid_sr = {"student_id": "s1", "wrong_question_ids": [1]}
        mock_llm = _make_llm_mock(side_effect=RuntimeError("API down"))
        with (
            patch("packages.agents.llm.complete_json_chat", mock_llm),
            pytest.raises(ValueError, match="Diagnostician agent failed"),
        ):
            await diagnostician_graph_node(cast("OhMyClassState", {"student_responses": valid_sr}))

    @pytest.mark.asyncio
    async def test_fails_closed_on_invalid_student_response(self):
        """Present but schema-invalid student_responses → ValidationError propagates."""
        from pydantic import ValidationError

        from packages.agents.sub_agents.diagnostician.agent import diagnostician_graph_node

        invalid_sr = {"student_id": "s1"}  # missing required wrong_question_ids
        with pytest.raises(ValidationError):
            await diagnostician_graph_node(cast("OhMyClassState", {"student_responses": invalid_sr}))  # noqa: E501


# ── adapter input validation ───────────────────────────────────────────────────

class TestExtractDiagnosticianState:
    def test_validates_student_response_schema(self):
        from packages.agents.sub_agents.diagnostician.adapters import extract_diagnostician_state

        valid = {
            "student_responses": {"student_id": "s1", "wrong_question_ids": [1, 2]},
            "run_id": "r1",
            "current_step": 0,
        }
        state = extract_diagnostician_state(valid)
        assert state["student_responses"]["student_id"] == "s1"
        assert state["student_responses"]["wrong_question_ids"] == [1, 2]

    def test_raises_on_invalid_student_response(self):
        """Invalid input (present but missing required fields) raises ValidationError — fail closed."""  # noqa: E501
        from pydantic import ValidationError

        from packages.agents.sub_agents.diagnostician.adapters import extract_diagnostician_state

        with pytest.raises(ValidationError):
            extract_diagnostician_state({
                "student_responses": {"student_id": "s1"},  # missing wrong_question_ids
            })

    def test_empty_dict_passes_through(self):
        from packages.agents.sub_agents.diagnostician.adapters import extract_diagnostician_state

        state = extract_diagnostician_state({"student_responses": {}})
        assert state["student_responses"] == {}

    def test_raises_on_invalid_field_types(self):
        from pydantic import ValidationError

        from packages.agents.sub_agents.diagnostician.adapters import extract_diagnostician_state

        with pytest.raises(ValidationError):
            extract_diagnostician_state({
                "student_responses": {
                    "student_id": "s1",
                    "wrong_question_ids": "not-a-list",  # wrong type
                },
            })
