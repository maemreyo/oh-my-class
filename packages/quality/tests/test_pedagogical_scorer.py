"""Tests for PedagogicalScore dataclass and score_pedagogical (QG2)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestPedagogicalScoreDataclass:
    def test_passed_true_when_total_gte_threshold(self):
        from packages.quality.layer4_judge.pedagogical_scorer import (
            PASS_THRESHOLD,
            PedagogicalScore,
        )
        score = PedagogicalScore(
            clarity=4.0, integrity=4.0, depth=3.5,
            practicality=4.0, pertinence=3.5,
            total=3.8, passed=True, rationale='good'
        )
        assert score.passed is True
        assert score.total >= PASS_THRESHOLD

    def test_passed_false_when_total_below_threshold(self):
        from packages.quality.layer4_judge.pedagogical_scorer import (
            PASS_THRESHOLD,
            PedagogicalScore,
        )
        score = PedagogicalScore(
            clarity=2.0, integrity=2.0, depth=3.0,
            practicality=2.0, pertinence=3.0,
            total=2.4, passed=False, rationale='poor'
        )
        assert score.passed is False
        assert score.total < PASS_THRESHOLD

    def test_pass_threshold_is_3_5(self):
        from packages.quality.layer4_judge.pedagogical_scorer import PASS_THRESHOLD
        assert PASS_THRESHOLD == 3.5

    def test_score_has_all_5_dimensions(self):
        from packages.quality.layer4_judge.pedagogical_scorer import PedagogicalScore
        score = PedagogicalScore(
            clarity=4.0, integrity=3.5, depth=4.0,
            practicality=3.5, pertinence=4.0,
            total=3.8, passed=True, rationale='ok'
        )
        assert score.clarity == 4.0
        assert score.integrity == 3.5
        assert score.depth == 4.0
        assert score.practicality == 3.5
        assert score.pertinence == 4.0

    def test_total_is_rounded(self):
        from packages.quality.layer4_judge.pedagogical_scorer import PedagogicalScore
        score = PedagogicalScore(
            clarity=4.0, integrity=3.0, depth=4.0,
            practicality=3.0, pertinence=4.0,
            total=3.6, passed=True, rationale=''
        )
        # 2 decimal places
        assert isinstance(score.total, float)
        assert len(str(score.total).split('.')[-1]) <= 2


class TestScorePedagogical:
    @pytest.mark.asyncio
    async def test_returns_pedagogical_score_from_llm(self):
        from packages.quality.layer4_judge.pedagogical_scorer import score_pedagogical

        mock_response = MagicMock()
        mock_response.content = '{"clarity": 4, "integrity": 4, "depth": 4, "practicality": 4, "pertinence": 4, "rationale": "good"}'  # noqa: E501

        mock_llm = AsyncMock()
        mock_llm.chat = AsyncMock(return_value=mock_response)

        result = await score_pedagogical('Some educational content.', llm=mock_llm)

        assert result.clarity == 4.0
        assert result.integrity == 4.0
        assert result.depth == 4.0
        assert result.practicality == 4.0
        assert result.pertinence == 4.0
        assert result.total == 4.0
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_passed_false_when_avg_below_threshold(self):
        from packages.quality.layer4_judge.pedagogical_scorer import score_pedagogical

        mock_response = MagicMock()
        mock_response.content = '{"clarity": 2, "integrity": 2, "depth": 3, "practicality": 2, "pertinence": 3, "rationale": "needs work"}'  # noqa: E501

        mock_llm = AsyncMock()
        mock_llm.chat = AsyncMock(return_value=mock_response)

        result = await score_pedagogical('Poor content.', llm=mock_llm)

        assert result.total < 3.5
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_raises_on_invalid_json(self):
        import json

        from packages.quality.layer4_judge.pedagogical_scorer import score_pedagogical

        mock_response = MagicMock()
        mock_response.content = 'Not valid JSON at all'

        mock_llm = AsyncMock()
        mock_llm.chat = AsyncMock(return_value=mock_response)

        with pytest.raises(json.JSONDecodeError):
            await score_pedagogical('content', llm=mock_llm)

    @pytest.mark.asyncio
    async def test_content_truncated_to_6000_chars(self):
        from packages.quality.layer4_judge.pedagogical_scorer import (
            _MAX_CONTENT_CHARS,
            score_pedagogical,
        )

        mock_response = MagicMock()
        mock_response.content = '{"clarity": 3, "integrity": 3, "depth": 3, "practicality": 3, "pertinence": 3, "rationale": "ok"}'  # noqa: E501

        mock_llm = AsyncMock()
        mock_llm.chat = AsyncMock(return_value=mock_response)

        long_content = 'A' * 10_000
        await score_pedagogical(long_content, llm=mock_llm)

        call_args = mock_llm.chat.call_args
        prompt = call_args[1]['messages'][0].content
        # The content section should be truncated
        assert 'A' * (_MAX_CONTENT_CHARS + 1) not in prompt
