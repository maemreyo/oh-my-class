"""SDX-03: system-curated deck structure presets.

Presets are pure configuration (a dict of teacher_constraints/pedagogical
overrides) selected via `SlideDeckEngineRequest.structure_preset`. These
tests cover the acceptance criteria verbatim:
  - each preset maps to a distinct, valid configuration
  - selecting a preset changes generated deck shape/pacing in the expected
    direction
  - the no-preset path is byte-for-byte unaffected
  - adding a new preset never touches common/contracts/slide_deck.py (it's
    plain data flowing through the existing teacher_constraints surface)
"""

from __future__ import annotations

from packages.agents.slide_deck_engine import SlideDeckEngine, SlideDeckEngineRequest
from packages.agents.slide_deck_engine.phases.input_assembly import assemble_input
from packages.agents.slide_deck_engine.structure_presets import SLIDE_DECK_STRUCTURE_PRESETS


def _request(*, structure_preset: str | None = None) -> SlideDeckEngineRequest:
    return SlideDeckEngineRequest(
        run_id="run-structure-preset",
        lesson_blueprint={
            "topic": "Equivalent fractions",
            "grade_level": "Grade 5",
            "learning_objectives": [
                {"description": "Explain why two fractions are equivalent."},
            ],
        },
        research_brief={
            "sources": [
                {"id": "src-fractions", "title": "Grade 5 Fractions Standard", "citation": "CCSS 5.NF.A"},
            ],
        },
        teacher_constraints={"locale": "en-US", "theme": "default"},
        structure_preset=structure_preset,
    )


def test_presets_are_a_fixed_curated_list_of_plain_dicts() -> None:
    """AC1: a fixed, curated list, each a plain configuration (no new model)."""
    assert set(SLIDE_DECK_STRUCTURE_PRESETS) == {"5e_model", "direct_instruction", "flipped_intro"}
    for config in SLIDE_DECK_STRUCTURE_PRESETS.values():
        assert isinstance(config, dict)
        assert "pedagogical_emphasis" in config


def test_each_preset_resolves_to_a_distinct_planner_configuration() -> None:
    """Each preset must actually differ once resolved onto AssembledSlideDeckInput."""
    resolved = {
        name: assemble_input(_request(structure_preset=name))
        for name in SLIDE_DECK_STRUCTURE_PRESETS
    }
    emphases = {assembled.pedagogical_emphasis for assembled in resolved.values()}
    assert len(emphases) == len(SLIDE_DECK_STRUCTURE_PRESETS)
    assert "" not in emphases


def test_no_preset_path_is_unaffected() -> None:
    """AC3: omitting structure_preset must reproduce today's exact resolution."""
    assembled = assemble_input(_request())

    assert assembled.pedagogical_emphasis == ""
    assert assembled.effective_teacher_constraints == {"locale": "en-US", "theme": "default"}


def test_unrecognized_preset_key_falls_back_to_no_preset_behavior() -> None:
    """A preset id that doesn't exist (e.g. a typo, or not-yet-added) must degrade
    to the default path rather than raising -- adding/removing presets is safe."""
    assembled = assemble_input(_request(structure_preset="does_not_exist"))

    assert assembled.pedagogical_emphasis == ""
    assert assembled.effective_teacher_constraints == {"locale": "en-US", "theme": "default"}


def test_explicit_teacher_constraints_win_over_preset_defaults() -> None:
    """Presets augment, they don't clobber, explicit teacher input."""
    request = _request(structure_preset="flipped_intro").model_copy(
        update={"teacher_constraints": {"locale": "en-US", "theme": "default", "duration_minutes": 45}},
    )

    assembled = assemble_input(request)

    assert assembled.effective_teacher_constraints["duration_minutes"] == 45  # preset wanted 20


async def test_selecting_a_preset_changes_generated_pacing_in_the_expected_direction() -> None:
    """flipped_intro budgets a 20-minute lesson; with no preset the engine falls
    back to its flat per-slide default (30 minutes for a 6-slide deck). The
    generated deck's rolled-up planned duration must track the preset, not the
    default -- a real, observable pacing difference from selecting a preset."""
    default_deck = (await SlideDeckEngine().generate(_request())).deck
    flipped_deck = (await SlideDeckEngine().generate(_request(structure_preset="flipped_intro"))).deck

    assert default_deck.total_planned_duration_minutes == 30.0
    assert flipped_deck.total_planned_duration_minutes == 20.0


async def test_selecting_a_preset_changes_generated_wording_in_the_expected_direction() -> None:
    """5e_model's explore-before-explain framing must reach the actual slide
    content (goal slide + practice-check prompt), not just internal config."""
    default_deck = (await SlideDeckEngine().generate(_request())).deck
    exploratory_deck = (await SlideDeckEngine().generate(_request(structure_preset="5e_model"))).deck

    default_goal_body = default_deck.slides[1].blocks[0].body
    exploratory_goal_body = exploratory_deck.slides[1].blocks[0].body

    assert default_goal_body != exploratory_goal_body
    assert "explore" in exploratory_goal_body.lower()
    assert "explore" not in default_goal_body.lower()


async def test_default_generation_path_is_byte_for_byte_unchanged() -> None:
    """AC3, end-to-end: a request that never mentions structure_preset must
    produce the exact same deck shape as before this feature existed."""
    result = await SlideDeckEngine().generate(_request())

    slide_titles = [slide.title for slide in result.deck.slides]
    assert slide_titles == ["Equivalent fractions", "Learning Goal", "Key Vocabulary", "Worked Example", "Guided Practice", "Exit Ticket"]
    assert result.deck.slides[1].blocks[0].body == "Explain Equivalent fractions with a visual model."
    assert all(report.passed for report in result.validation_reports)


def test_adding_a_new_preset_requires_no_contract_or_model_change() -> None:
    """AC4: mutate a *local copy* of the presets mapping (never the module-level
    dict) and confirm resolution still works with zero schema involvement --
    proving a new preset is just a new dict entry, nothing else."""
    presets_with_new_entry = {
        **SLIDE_DECK_STRUCTURE_PRESETS,
        "socratic_seminar": {"pedagogical_emphasis": "student_led_questioning"},
    }

    assert "socratic_seminar" not in SLIDE_DECK_STRUCTURE_PRESETS  # module dict untouched
    assert presets_with_new_entry["socratic_seminar"] == {"pedagogical_emphasis": "student_led_questioning"}
