"""Tests for Roadmap Agent and supporting tools."""

import json
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from common.contracts.student_profile import LearningStyle, PersonalityTrait, StudentProfile

if TYPE_CHECKING:
    from packages.agents.sub_agents.roadmap_agent.state import RoadmapAgentState

# ── StudentProfile ────────────────────────────────────────────────────────────

class TestLearningStyle:
    def test_valid_visual(self):
        style = LearningStyle(primary="visual")
        assert style.primary == "visual"
        assert style.media_preference is None
        assert style.format_preference is None

    def test_with_all_fields(self):
        style = LearningStyle(
            primary="auditory",
            media_preference="podcast",
            format_preference="1v1",
        )
        assert style.media_preference == "podcast"

    def test_film_learner(self):
        style = LearningStyle(primary="visual", media_preference="film")
        assert style.media_preference == "film"


class TestPersonalityTrait:
    def test_valid(self):
        trait = PersonalityTrait(
            trait="shy",
            vn_name="Nhút nhát",
            teaching_principle="Avoid group pressure; use self-paced activities",
        )
        assert trait.trait == "shy"
        assert "nhút nhát" in trait.vn_name.lower()

    def test_depth_oriented(self):
        trait = PersonalityTrait(
            trait="depth_oriented",
            vn_name="Học sâu",
            teaching_principle="Explain root causes before practice",
        )
        assert trait.trait == "depth_oriented"


class TestStudentProfile:
    def _make_minimal(self) -> dict[str, Any]:
        return {
            "student_id": "s1",
            "learning_style": {"primary": "visual"},
        }

    def test_minimal_defaults(self):
        profile = StudentProfile.model_validate(self._make_minimal())
        assert profile.student_id == "s1"
        assert profile.personality_traits == []
        assert profile.weaknesses == []
        assert profile.strengths == []
        assert profile.target_score is None
        assert profile.target_exam is None
        assert profile.study_duration_months == 6
        assert profile.tools == []
        assert profile.raw_context == ""

    def test_with_all_fields(self):
        data = {
            "student_id": "s2",
            "learning_style": {"primary": "reading", "media_preference": "text"},
            "personality_traits": [
                {"trait": "shy", "vn_name": "Nhút nhát", "teaching_principle": "Self-paced"}
            ],
            "weaknesses": ["vocabulary", "collocation"],
            "strengths": ["grammar"],
            "target_score": 40,
            "target_exam": "HSA",
            "study_duration_months": 6,
            "tools": ["google_classroom"],
            "raw_context": "Student is shy and struggles with vocabulary.",
        }
        profile = StudentProfile.model_validate(data)
        assert profile.target_score == 40
        assert profile.target_exam == "HSA"
        assert "vocabulary" in profile.weaknesses
        assert len(profile.personality_traits) == 1

    def test_model_dump_roundtrip(self):
        profile = StudentProfile(
            student_id="s3",
            learning_style=LearningStyle(primary="kinesthetic"),
            study_duration_months=4,
        )
        dumped = profile.model_dump()
        restored = StudentProfile.model_validate(dumped)
        assert restored.study_duration_months == 4

    def test_exported_from_contracts(self):
        from common.contracts import StudentProfile as StudentProfileAlias
        assert StudentProfileAlias is StudentProfile


class TestStudentProfileLiterals:
    def test_rejects_invalid_learning_style_primary(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            StudentProfile(
                student_id="s1",
                learning_style=LearningStyle(primary="mixed"),  # pyright: ignore[reportArgumentType]
            )

    def test_rejects_invalid_target_exam(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            StudentProfile(
                student_id="s1",
                learning_style=LearningStyle(primary="visual"),
                target_exam="SAT",  # pyright: ignore[reportArgumentType]
            )

    def test_accepts_all_valid_target_exams(self):
        for exam in ["HSA", "IELTS", "TOEIC"]:
            p = StudentProfile(
                student_id="s1",
                learning_style=LearningStyle(primary="visual"),
                target_exam=exam,  # pyright: ignore[reportArgumentType]
            )
            assert p.target_exam == exam

    def test_accepts_none_target_exam(self):
        p = StudentProfile(
            student_id="s1",
            learning_style=LearningStyle(primary="auditory"),
        )
        assert p.target_exam is None

    def test_rejects_study_duration_below_minimum(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            StudentProfile(
                student_id="s1",
                learning_style=LearningStyle(primary="visual"),
                study_duration_months=0,
            )

    def test_rejects_study_duration_above_maximum(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            StudentProfile(
                student_id="s1",
                learning_style=LearningStyle(primary="visual"),
                study_duration_months=25,
            )


# ── Roadmap Agent Tools ────────────────────────────────────────────────────────

class TestBookRecommender:
    def test_b2_level_returns_core_books(self):
        from packages.agents.sub_agents.roadmap_agent.tools import book_recommender

        result = book_recommender("B2", [])
        assert result["level"] == "B2"
        assert len(result["core_books"]) > 0
        titles = [b["title"] for b in result["core_books"]]
        assert any("B2" in t for t in titles)

    def test_b1_level(self):
        from packages.agents.sub_agents.roadmap_agent.tools import book_recommender

        result = book_recommender("B1", ["grammar"])
        assert result["level"] == "B1"
        assert len(result["core_books"]) > 0

    def test_c1_level(self):
        from packages.agents.sub_agents.roadmap_agent.tools import book_recommender

        result = book_recommender("C1", [])
        assert result["level"] == "C1"
        titles = [b["title"] for b in result["core_books"]]
        assert any("C1" in t for t in titles)

    def test_with_weak_skills_adds_supplements(self):
        from packages.agents.sub_agents.roadmap_agent.tools import book_recommender

        result = book_recommender("B2", ["vocabulary", "collocation"])
        assert len(result["supplement_books"]) > 0

    def test_unknown_level_falls_back_to_b2(self):
        from packages.agents.sub_agents.roadmap_agent.tools import book_recommender

        result = book_recommender("A1", [])
        assert result["level"] == "A1"
        assert len(result["core_books"]) > 0

    def test_no_duplicate_supplements(self):
        from packages.agents.sub_agents.roadmap_agent.tools import book_recommender

        result = book_recommender("B2", ["vocabulary", "vocabulary"])
        titles = [b["title"] for b in result["supplement_books"]]
        assert len(titles) == len(set(titles))


class TestMilestoneCalculator:
    def test_returns_correct_month_count(self):
        from packages.agents.sub_agents.roadmap_agent.tools import milestone_calculator

        milestones = milestone_calculator(40, 0.6, 6)
        assert len(milestones) == 6

    def test_month_numbers_sequential(self):
        from packages.agents.sub_agents.roadmap_agent.tools import milestone_calculator

        milestones = milestone_calculator(40, 0.5, 4)
        months = [m["month"] for m in milestones]
        assert months == [1, 2, 3, 4]

    def test_final_score_reaches_target(self):
        from packages.agents.sub_agents.roadmap_agent.tools import milestone_calculator

        milestones = milestone_calculator(40, 0.5, 6)
        final = milestones[-1]["target_score"]
        assert final == 40

    def test_scores_are_non_decreasing(self):
        from packages.agents.sub_agents.roadmap_agent.tools import milestone_calculator

        milestones = milestone_calculator(40, 0.6, 6)
        scores = [m["target_score"] for m in milestones]
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i - 1]

    def test_each_milestone_has_focus(self):
        from packages.agents.sub_agents.roadmap_agent.tools import milestone_calculator

        milestones = milestone_calculator(40, 0.4, 3)
        for m in milestones:
            assert "focus" in m
            assert len(m["focus"]) > 0

    def test_low_error_rate_starts_higher(self):
        from packages.agents.sub_agents.roadmap_agent.tools import milestone_calculator

        high_error = milestone_calculator(40, 0.8, 6)[0]["target_score"]
        low_error = milestone_calculator(40, 0.2, 6)[0]["target_score"]
        assert low_error >= high_error


# ── Roadmap Agent node ─────────────────────────────────────────────────────────

def _make_llm_mock(
    return_value: str | None = None,
    side_effect: Exception | None = None,
) -> AsyncMock:
    if side_effect is not None:
        return AsyncMock(side_effect=side_effect)
    return AsyncMock(return_value=return_value)


VALID_ROADMAP_JSON = json.dumps({
    "title": "Lộ trình học tập cá nhân — s1",
    "hero": {
        "eyebrow": "Lộ trình học tập",
        "title": "HSA 40+ trong 6 tháng",
        "lede": "Kế hoạch học tập được cá nhân hóa.",
        "stamp": "HSA 40+",
    },
    "sidebar": {"title": "Lộ trình", "subtitle": "6 tháng"},
    "sections": [
        {
            "id": "phase-1",
            "title": "Tháng 1: Nền tảng",
            "components": [
                {
                    "type": "phase_timeline",
                    "phases": [
                        {
                            "title": "Tuần 1-2: Ngữ pháp",
                            "when": "Tháng 1",
                            "goal": "Ôn tập thì động từ cơ bản",
                            "group": "a",
                            "blocks": [{"label": "Sách", "value": "Destination B2 Unit 1"}],
                            "output": "Đạt 80% bài kiểm tra",
                        }
                    ],
                }
            ],
        }
    ],
})

VALID_ROADMAP_WRAPPED = f"```json\n{VALID_ROADMAP_JSON}\n```"


class TestRoadmapNode:
    def _make_state(self, **overrides) -> dict[str, Any]:
        from packages.agents.teaching_pack.stages import StageEnum

        base = {
            "diagnostic_report": {
                "student_id": "s1",
                "knowledge_gaps": [],
                "bloom_gaps": [],
                "misconception_patterns": [],
                "critical_sections": [],
                "overall_error_rate": 0.5,
                "recommended_level": "B2",
                "summary": "Cần ôn tập ngữ pháp.",
            },
            "student_profile": {
                "student_id": "s1",
                "learning_style": {"primary": "visual"},
                "target_score": 40,
                "target_exam": "HSA",
                "study_duration_months": 6,
            },
            "run_id": "test-run-001",
            "current_step": StageEnum.UNIT_PREP,
        }
        base.update(overrides)
        return base

    @pytest.mark.asyncio
    async def test_returns_roadmap_artifact(self):
        from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node

        mock_llm = _make_llm_mock(return_value=VALID_ROADMAP_WRAPPED)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await roadmap_node(cast("RoadmapAgentState", self._make_state()))

        assert "roadmap_artifact" in result
        assert "artifacts" in result
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["type"] == "roadmap"

    @pytest.mark.asyncio
    async def test_roadmap_artifact_has_sections(self):
        from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node

        mock_llm = _make_llm_mock(return_value=VALID_ROADMAP_WRAPPED)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await roadmap_node(cast("RoadmapAgentState", self._make_state()))

        artifact = result["roadmap_artifact"]
        assert "sections" in artifact
        assert len(artifact["sections"]) > 0

    @pytest.mark.asyncio
    async def test_artifact_type_set_to_roadmap(self):
        from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node

        mock_llm = _make_llm_mock(return_value=VALID_ROADMAP_JSON)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await roadmap_node(cast("RoadmapAgentState", self._make_state()))

        assert result["roadmap_artifact"]["artifact_type"] == "roadmap"

    @pytest.mark.asyncio
    async def test_raises_value_error_on_invalid_json(self):
        from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node

        mock_llm = _make_llm_mock(return_value="not json")
        with (
            patch("packages.agents.llm.complete_json_chat", mock_llm),
            pytest.raises(ValueError, match="Invalid JSON"),
        ):
            await roadmap_node(cast("RoadmapAgentState", self._make_state()))

    @pytest.mark.asyncio
    async def test_raises_value_error_on_llm_error(self):
        from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node

        mock_llm = _make_llm_mock(side_effect=RuntimeError("API timeout"))
        with (
            patch("packages.agents.llm.complete_json_chat", mock_llm),
            pytest.raises(ValueError, match="Roadmap agent failed"),
        ):
            await roadmap_node(cast("RoadmapAgentState", self._make_state()))

    @pytest.mark.asyncio
    async def test_works_without_student_profile(self):
        from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node

        mock_llm = _make_llm_mock(return_value=VALID_ROADMAP_JSON)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await roadmap_node(cast("RoadmapAgentState", self._make_state(student_profile=None)))  # noqa: E501

        assert "roadmap_artifact" in result

    @pytest.mark.asyncio
    async def test_artifact_entry_has_student_id_in_id(self):
        from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node

        mock_llm = _make_llm_mock(return_value=VALID_ROADMAP_JSON)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await roadmap_node(cast("RoadmapAgentState", self._make_state()))

        artifact_id = result["artifacts"][0]["id"]
        assert "s1" in artifact_id


# ── roadmap node validates RoadmapContent schema ──────────────────────────────

class TestRoadmapNodeValidation:
    def _make_state(self) -> dict[str, Any]:
        from packages.agents.teaching_pack.stages import StageEnum

        return {
            "diagnostic_report": {
                "student_id": "s1",
                "knowledge_gaps": [],
                "bloom_gaps": [],
                "misconception_patterns": [],
                "critical_sections": [],
                "overall_error_rate": 0.5,
                "recommended_level": "B2",
                "summary": "Cần ôn tập.",
            },
            "run_id": "r1",
            "current_step": StageEnum.UNIT_PREP,
        }

    @pytest.mark.asyncio
    async def test_valid_output_passes_pydantic(self):
        from common.contracts.roadmap import RoadmapContent
        from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node

        mock_llm = _make_llm_mock(return_value=VALID_ROADMAP_JSON)
        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            result = await roadmap_node(cast("RoadmapAgentState", self._make_state()))

        validated = RoadmapContent.model_validate(result["roadmap_artifact"])
        assert validated.hero.title == "HSA 40+ trong 6 tháng"
        assert validated.sidebar.subtitle == "6 tháng"

    @pytest.mark.asyncio
    async def test_invalid_output_raises_schema_error(self):
        from packages.agents.sub_agents.roadmap_agent.nodes import roadmap_node

        bad_roadmap = json.dumps({"title": "test"})  # missing required hero + sidebar
        mock_llm = _make_llm_mock(return_value=bad_roadmap)
        with (
            patch("packages.agents.llm.complete_json_chat", mock_llm),
            pytest.raises(ValueError, match="Roadmap agent failed"),
        ):
            await roadmap_node(cast("RoadmapAgentState", self._make_state()))
