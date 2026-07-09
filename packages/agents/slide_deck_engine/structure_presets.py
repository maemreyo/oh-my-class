"""System-curated slide-deck structure presets (SDX-03, ADR-047).

A fixed, curated list a teacher can pick at deck-creation time as a starting
point. Presets are pure configuration: plain dicts of overrides fed into the
engine's existing configuration surface — `teacher_constraints` (read by
`deck_shape.evaluate_deck_shape`'s optional-slide budget) and
`pedagogical_emphasis` (read by `plan_pedagogy`'s framing). Adding a preset
here is a dict entry; it never requires touching `common/contracts/slide_deck.py`
or any Pydantic model, because no new contract type is introduced.

No mechanism exists (here or anywhere else) for a teacher to save an
arbitrary deck's structure as a new preset — this is the full, curated set
for this slice. Personalized templates are deferred until the engine gains
phase-level checkpoint/resume for another reason (see the SDX-03 issue).
"""

from __future__ import annotations

from typing import Final

from common.contracts.run_contract import JsonObject

SLIDE_DECK_STRUCTURE_PRESETS: Final[dict[str, JsonObject]] = {
    # 5E model (Engage-Explore-Explain-Elaborate-Evaluate): front-load
    # exploration before naming the pattern, and budget for the extra
    # slide a full 5E pass tends to need.
    "5e_model": {
        "pedagogical_emphasis": "explore_before_explain",
        "topic_complexity": "high",
        "requested_extra_slides": 1,
    },
    # Direct instruction: teacher models first, students practice the same
    # pattern immediately after. No extra slide budget — this is the
    # tightest, most literal reading of the required six-slide spine.
    "direct_instruction": {
        "pedagogical_emphasis": "model_then_practice",
    },
    # Flipped intro: students arrive with prior exposure (video/reading);
    # class time recaps and builds on it, so it also fits in a shorter slot.
    "flipped_intro": {
        "pedagogical_emphasis": "prior_exposure_recap",
        "duration_minutes": 20,
    },
}
