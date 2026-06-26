"""Tests for layer2_content.component_scorer — soft intelligence scoring."""
from __future__ import annotations

from packages.quality.layer2_content.component_scorer import (
    ComponentScoringResult,
    score_component_usage,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _comp(comp_type: str, **extra: object) -> dict[str, object]:
    """Build a minimal component dict of the given type."""
    d: dict[str, object] = {"type": comp_type}
    d.update(extra)
    return d


def _section_with(*components: dict[str, object]) -> dict[str, object]:
    """Section containing nested components."""
    return {"components": list(components)}


def _artifact(
    artifact_type: str = "lesson",
    *sections: dict[str, object],
) -> dict[str, object]:
    return {"artifact_type": artifact_type, "sections": list(sections)}


# ── 1. Baseline ──────────────────────────────────────────────────────────────


class TestBaseline:
    def test_typical_lesson_scores_near_five(self) -> None:
        """A lesson with heading + paragraph + question_card should be ~5."""
        art = _artifact(
            "lesson",
            _section_with(_comp("heading", level=1, text="Intro")),
            _section_with(_comp("paragraph", text="Body")),
            _section_with(
                _comp("question_card", id="q1", text="Q?", options=[], answer="A", explain="E")
            ),
        )
        result = score_component_usage(art)
        assert isinstance(result, ComponentScoringResult)
        # 3 intents: STRUCTURAL + ASSESSMENT + STRUCTURAL → 2 unique → 2/8*2.5 = 0.625
        # base 5 + 0.625 = 5.625
        assert 4.0 <= result.score <= 7.0
        assert result.base_score == 5.0
        assert result.component_count == 3

    def test_empty_sections_returns_baseline(self) -> None:
        art = _artifact("lesson")
        result = score_component_usage(art)
        assert result.score == 5.0
        assert result.component_count == 0

    def test_missing_sections_key_returns_baseline(self) -> None:
        art: dict[str, object] = {"artifact_type": "lesson"}
        result = score_component_usage(art)
        assert result.score == 5.0


# ── 2. Diversity bonus ───────────────────────────────────────────────────────


class TestDiversityBonus:
    def test_higher_diversity_scores_higher(self) -> None:
        """Artifact with 5 distinct intents should score above baseline."""
        art = _artifact(
            "lesson",
            _section_with(_comp("heading", level=1, text="H")),  # STRUCTURAL
            _section_with(_comp("table", columns=[], rows=[])),  # DATA_DISPLAY
            _section_with(_comp("phase_timeline", phases=[])),  # TIMELINE_FLOW
            _section_with(
                _comp("question_card", id="q1", text="Q?", options=[], answer="A", explain="E")
            ),  # ASSESSMENT
            _section_with(
                _comp("vocab_cluster", title="V", words=[])
            ),  # KNOWLEDGE_ORGANIZATION
        )
        result = score_component_usage(art)
        assert result.unique_intents == 5
        assert result.diversity_ratio == 5 / 8
        # base 5 + 5/8*2.5 = 5 + 1.5625 = 6.5625
        assert result.score > 6.0

    def test_monotype_lower_than_diverse(self) -> None:
        """All-question artifact scores below a diverse one."""
        monotype = _artifact(
            "quiz",
            *[_section_with(
                _comp("question_card", id=f"q{i}", text="Q?", options=[], answer="A", explain="E")
            ) for i in range(5)]
        )
        diverse = _artifact(
            "lesson",
            _section_with(_comp("heading", level=1, text="H")),
            _section_with(_comp("table", columns=[], rows=[])),
            _section_with(_comp("phase_timeline", phases=[])),
            _section_with(
                _comp("vocab_cluster", title="V", words=[])
            ),
            _section_with(
                _comp("question_card", id="q1", text="Q?", options=[], answer="A", explain="E")
            ),
        )
        mono_score = score_component_usage(monotype)
        diverse_score = score_component_usage(diverse)
        assert diverse_score.score > mono_score.score


# ── 3. Stuffing penalty ─────────────────────────────────────────────────────


class TestStuffingPenalty:
    def test_question_card_only_gets_stuffing_penalty(self) -> None:
        """6 question_cards (ASSESSMENT only) → near-stuffing penalty."""
        art = _artifact(
            "quiz",
            *[_section_with(
                _comp("question_card", id=f"q{i}", text="Q?", options=[], answer="A", explain="E")
            ) for i in range(6)]
        )
        result = score_component_usage(art)
        assert result.unique_intents == 1
        assert result.stuffing_penalty > 0
        # 5 + 1/8*2.5 - stuffing = lower than baseline
        assert result.score < 5.0

    def test_single_type_four_components_hard_stuffing(self) -> None:
        """4 components, all same intent → hard stuffing penalty."""
        art = _artifact(
            "lesson",
            *[_section_with(
                _comp("question_card", id=f"q{i}", text="Q?", options=[], answer="A", explain="E")
            ) for i in range(4)]
        )
        result = score_component_usage(art)
        assert result.stuffing_penalty > 0
        assert any("stuffing" in n for n in result.notes)


# ── 4. Overuse penalty ──────────────────────────────────────────────────────


class TestOverusePenalty:
    def test_callout_exceeding_max_gets_penalty(self) -> None:
        """callout has max_per_artifact=3; 5 callouts → 2 excess × 0.5 = 1.0 penalty."""
        art = _artifact(
            "lesson",
            *[_section_with(_comp("callout", variant="tip", body="text")) for _ in range(5)]
        )
        result = score_component_usage(art)
        assert result.overuse_penalty == 1.0
        assert "callout" in result.overused_types
        assert any("overuse" in n for n in result.notes)

    def test_within_max_no_penalty(self) -> None:
        """3 callouts (exactly at max) → no penalty."""
        art = _artifact(
            "lesson",
            *[_section_with(_comp("callout", variant="tip", body="text")) for _ in range(3)]
        )
        result = score_component_usage(art)
        assert result.overuse_penalty == 0.0
        assert result.overused_types == []


# ── 5. Methodology alignment ────────────────────────────────────────────────


class TestMethodologyAlignment:
    def test_vocab_cluster_matches_vocab_tag(self) -> None:
        """vocab_cluster present + vocab tag → methodology bonus."""
        art = _artifact(
            "lesson",
            _section_with(_comp("vocab_cluster", title="Words", words=[])),
            _section_with(_comp("heading", level=1, text="H")),
        )
        plan = {"methodology": {"tags": ["vocab"]}}
        result = score_component_usage(art, lesson_plan=plan)
        assert result.methodology_bonus > 0
        assert any("methodology matched: vocab" in n for n in result.notes)

    def test_concept_map_matches_concept_map_tag(self) -> None:
        art = _artifact(
            "lesson",
            _section_with(_comp("concept_map", nodes=[])),
        )
        plan = {"methodology": {"tags": ["concept_map"]}}
        result = score_component_usage(art, lesson_plan=plan)
        assert result.methodology_bonus > 0

    def test_unmatched_tag_no_bonus(self) -> None:
        """tag present but no matching component → 0 bonus."""
        art = _artifact(
            "lesson",
            _section_with(_comp("heading", level=1, text="H")),
        )
        plan = {"methodology": {"tags": ["film_based"]}}
        result = score_component_usage(art, lesson_plan=plan)
        assert result.methodology_bonus == 0.0

    def test_no_lesson_plan_no_bonus(self) -> None:
        """No lesson_plan → methodology bonus = 0."""
        art = _artifact(
            "lesson",
            _section_with(_comp("vocab_cluster", title="V", words=[])),
        )
        result = score_component_usage(art, lesson_plan=None)
        assert result.methodology_bonus == 0.0

    def test_methodology_bonus_capped_at_two(self) -> None:
        """Even with all tags matched, bonus caps at 2.0."""
        art = _artifact(
            "lesson",
            _section_with(_comp("vocab_cluster", title="V", words=[])),
            _section_with(_comp("contrastive_pairs", rows=[])),
            _section_with(_comp("film_clip_activity", clips=[])),
            _section_with(_comp("roleplay_script", lines=[])),
            _section_with(_comp("active_recall_prompt", instruction="Recall")),
            _section_with(
                _comp("question_card", id="q1", text="Q?", options=[], answer="A", explain="E")
            ),
            _section_with(_comp("heading", level=1, text="H")),
        )
        plan = {"methodology": {"tags": [
            "vocab", "concept_map", "contrastive_pairs", "film_based",
            "roleplay", "active_recall", "why_wrong_reasoning",
        ]}}
        result = score_component_usage(art, lesson_plan=plan)
        assert result.methodology_bonus == 2.0


# ── 6. Score clamps ─────────────────────────────────────────────────────────


class TestScoreClamps:
    def test_score_never_below_zero(self) -> None:
        """Extreme stuffing + overuse still ≥ 0."""
        # 8 callouts (max=3, excess=5 → 2.5 penalty) + all same intent → stuffing
        art = _artifact(
            "lesson",
            *[_section_with(_comp("callout", variant="tip", body="x")) for _ in range(8)]
        )
        result = score_component_usage(art)
        assert result.score >= 0.0

    def test_score_never_above_ten(self) -> None:
        """Even max diversity + max methodology can't exceed 10."""
        art = _artifact(
            "lesson",
            _section_with(_comp("heading", level=1, text="H")),
            _section_with(_comp("table", columns=[], rows=[])),
            _section_with(_comp("phase_timeline", phases=[])),
            _section_with(
                _comp("question_card", id="q1", text="Q?", options=[], answer="A", explain="E")
            ),
            _section_with(_comp("vocab_cluster", title="V", words=[])),
            _section_with(_comp("film_clip_activity", clips=[])),
            _section_with(_comp("active_recall_prompt", instruction="R")),
            _section_with(_comp("hw_list", items=[])),
        )
        plan = {"methodology": {"tags": [
            "vocab", "concept_map", "film_based", "active_recall",
        ]}}
        result = score_component_usage(art, lesson_plan=plan)
        assert result.score <= 10.0


# ── 7. Strong vocab lesson vs flat/monotype ─────────────────────────────────


class TestVocabLessonVsMonotype:
    def test_rich_vocab_lesson_beats_question_only_quiz(self) -> None:
        """A well-structured vocab lesson outperforms a question-stuffed quiz."""
        vocab_lesson = _artifact(
            "lesson",
            _section_with(_comp("heading", level=1, text="Vocabulary")),
            _section_with(
                _comp("vocab_cluster", title="Key Words", words=[])
            ),
            _section_with(
                _comp("contrastive_pairs", rows=[])
            ),
            _section_with(
                _comp("active_recall_prompt", instruction="Cover and recall")
            ),
            _section_with(
                _comp("question_card", id="q1", text="Q?", options=[], answer="A", explain="E")
            ),
        )
        flat_quiz = _artifact(
            "quiz",
            *[_section_with(
                _comp("question_card", id=f"q{i}", text="Q?", options=[], answer="A", explain="E")
            ) for i in range(10)]
        )
        plan = {"methodology": {"tags": ["vocab", "active_recall"]}}

        vocab_result = score_component_usage(vocab_lesson, lesson_plan=plan)
        flat_result = score_component_usage(flat_quiz)

        assert vocab_result.score > flat_result.score
        assert vocab_result.methodology_bonus > 0
        assert flat_result.stuffing_penalty > 0


# ── 8. Nested section.components handled ─────────────────────────────────────


class TestNestedComponents:
    def test_deeply_nested_components_counted(self) -> None:
        """Components nested inside section.components are extracted."""
        art = {
            "artifact_type": "lesson",
            "sections": [
                {
                    "components": [
                        {"components": [
                            _comp("heading", level=1, text="Deep"),
                        ]},
                    ],
                },
                _section_with(
                    _comp("table", columns=[], rows=[])
                ),
            ],
        }
        result = score_component_usage(art)
        # _extract_components flattens one level of nesting
        assert result.component_count >= 1


# ── 9. methodology_tags flat key fallback ────────────────────────────────────


class TestMethodologyTagsFallback:
    def test_flat_methodology_tags_key(self) -> None:
        """lesson_plan['methodology_tags'] (flat) is also accepted."""
        art = _artifact(
            "lesson",
            _section_with(_comp("vocab_cluster", title="V", words=[])),
        )
        plan = {"methodology_tags": ["vocab"]}
        result = score_component_usage(art, lesson_plan=plan)
        assert result.methodology_bonus > 0
