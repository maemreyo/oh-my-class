from __future__ import annotations

from packages.agents.slide_deck_engine import SlideDeckEngine, SlideDeckEngineRequest


def test_esl_food_vocabulary_deck_uses_concrete_teachable_content() -> None:
    request = SlideDeckEngineRequest(
        run_id="run-food-vocab-quality",
        lesson_blueprint={
            "topic": "Grade 5 English ESL food vocabulary",
            "grade_level": "Grade 5",
            "learning_objectives": [
                {"description": "Use food vocabulary in short ESL speaking exchanges."},
            ],
        },
        research_brief={
            "sources": [
                {
                    "id": "src-food-vocab",
                    "title": "Teacher supplied ESL food vocabulary context",
                    "citation": "Teacher supplied lesson context",
                },
            ],
        },
        dependency_artifacts=[],
        teacher_constraints={"locale": "en-US", "theme": "default"},
        revision_feedback="",
    )

    result = SlideDeckEngine().generate(request)
    student_surface = " ".join([
        *[block.body for slide in result.deck.slides for block in slide.blocks],
        *[interaction.prompt for slide in result.deck.slides for interaction in (slide.interactions or [])],
        *[option.label for slide in result.deck.slides for interaction in (slide.interactions or []) for option in (interaction.options or [])],
    ]).lower()

    assert "apple" in student_surface
    assert "rice" in student_surface
    assert "water" in student_surface
    assert "i would like" in student_surface
    assert "what would you like to eat or drink" in student_surface
    assert "introduce three high-use words" not in student_surface
    assert "a clear example of grade 5 english esl food vocabulary" not in student_surface
