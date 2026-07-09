"""Purpose-aware deck shape and density guards (SDH-06), plus the ADR-045
pedagogical-role and planned-pacing layer built on top of it (SDTF-02).

Replaces raw slide-count/char-count thresholds with checks tied to what a
slide's pedagogical role actually needs. The v1 required spine is title,
goal, vocabulary, example, practice, and exit (ADR-040/041 slide-deck v1
shape). Anything beyond that spine is "optional" and must be justified by
duration, topic complexity, grade band, or an explicit teacher request.

SDTF-02 reconciliation: SDH-06's "purpose" (title/goal/vocabulary/example/
practice/exit/optional) and ADR-045's "pedagogical role" (hook/objective/
explain/model/guided_practice/check_understanding/independent_practice/
recap/exit_ticket) are the same underlying concept -- a slide's teaching
job, independent of its visual `layout` -- at two levels of granularity.
"Purpose" stays coarse (spine vs. optional) because that's all
`evaluate_deck_shape`'s budget check needs. "Role" is a thin typed layer on
top (`assign_pedagogical_roles`) that keeps the 1:1 spine mapping but also
names the common optional extensions, so density checks and teacher preview
can reason about them individually instead of lumping every extra slide
into one "optional" bucket.
"""

from __future__ import annotations

import re
from typing import Final, NamedTuple

from common.contracts.run_contract import JsonObject
from common.contracts.slide_deck import PedagogicalRole, SlideDeckData, SlideDeckSlide

from packages.agents.slide_deck_engine.models import (
    SlideDeckHealingScope,
    SlideDeckValidationCode,
    SlideDeckValidationReport,
)

# slide_id convention today is "slide-<purpose>[-<suffix>]"; aliases map the
# leading token to a canonical spine purpose. Unrecognized tokens fall back
# to "optional".
_PURPOSE_ALIASES: Final[dict[str, str]] = {
    "title": "title",
    "hook": "title",
    "goal": "goal",
    "objective": "goal",
    "vocabulary": "vocabulary",
    "vocab": "vocabulary",
    "context": "vocabulary",
    "example": "example",
    "worked": "example",
    "practice": "practice",
    "guided": "practice",
    "exit": "exit",
}
_REQUIRED_SPINE: Final[tuple[str, ...]] = ("title", "goal", "vocabulary", "example", "practice", "exit")

# Spine purpose -> ADR-045 role. 1:1 by construction: every required-spine
# purpose has exactly one canonical role.
_ROLE_BY_SPINE_PURPOSE: Final[dict[str, PedagogicalRole]] = {
    "title": "hook",
    "goal": "objective",
    "vocabulary": "explain",
    "example": "model",
    "practice": "guided_practice",
    "exit": "exit_ticket",
}
# Public, ordered view of the 6 required-spine roles (SDTF-07's component
# registry needs this to check spine coverage without re-deriving it from
# the purpose map above).
SPINE_ROLES: Final[tuple[PedagogicalRole, ...]] = tuple(_ROLE_BY_SPINE_PURPOSE.values())
# Optional-extension slide_id tokens that map to a named role beyond the
# spine. Anything else stays unassigned (None) rather than forced into a
# role it doesn't fit -- the taxonomy is deliberately small and extensible.
_OPTIONAL_ROLE_ALIASES: Final[dict[str, PedagogicalRole]] = {
    "independent": "independent_practice",
    "check": "check_understanding",
    "quiz": "check_understanding",
    "recap": "recap",
    "reflection": "recap",
    "review": "recap",
}


class PurposeDensityRule(NamedTuple):
    min_blocks: int
    min_total_chars: int
    max_total_chars: int
    requires_interaction: bool = False


# ponytail: thresholds calibrated against the current deterministic template
# output (roughly 2-3x headroom above it); revisit once SDE-01 real LLM
# content lands and SDH-07 evidence shows real decks need different bounds.
# Keyed by ADR-045 role (SDTF-02) rather than raw purpose/layout, so density
# expectations track what a slide is *for*, not how it's laid out.
_ROLE_DENSITY: Final[dict[str, PurposeDensityRule]] = {
    "hook": PurposeDensityRule(min_blocks=1, min_total_chars=15, max_total_chars=500),
    "objective": PurposeDensityRule(min_blocks=2, min_total_chars=60, max_total_chars=900),
    "explain": PurposeDensityRule(min_blocks=2, min_total_chars=60, max_total_chars=900),
    "model": PurposeDensityRule(min_blocks=2, min_total_chars=60, max_total_chars=900),
    "guided_practice": PurposeDensityRule(min_blocks=1, min_total_chars=15, max_total_chars=900, requires_interaction=True),
    "check_understanding": PurposeDensityRule(min_blocks=1, min_total_chars=15, max_total_chars=900, requires_interaction=True),
    "independent_practice": PurposeDensityRule(min_blocks=1, min_total_chars=15, max_total_chars=900, requires_interaction=True),
    "recap": PurposeDensityRule(min_blocks=1, min_total_chars=30, max_total_chars=900),
    "exit_ticket": PurposeDensityRule(min_blocks=1, min_total_chars=40, max_total_chars=900),
}
_DEFAULT_DENSITY_RULE: Final = PurposeDensityRule(min_blocks=1, min_total_chars=30, max_total_chars=900)

# Relative time weight per role for splitting total lesson minutes across
# slides (`estimate_slide_planned_minutes`). Heavier for roles where students
# do the work (guided/independent practice); lighter for quick transitions
# (hook, objective, recap, exit ticket).
_ROLE_PACING_WEIGHT: Final[dict[str, float]] = {
    "hook": 0.5,
    "objective": 0.5,
    "explain": 1.0,
    "model": 1.0,
    "guided_practice": 1.5,
    "check_understanding": 1.0,
    "independent_practice": 1.5,
    "recap": 0.5,
    "exit_ticket": 0.5,
}
_DEFAULT_ROLE_PACING_WEIGHT: Final = 1.0
# ponytail: flat per-slide planning default when the teacher hasn't set
# `duration_minutes`; revisit once SDH-07 evidence shows real lesson lengths.
_DEFAULT_MINUTES_PER_SLIDE: Final = 5.0

_GRADE_NUMBER_RE: Final = re.compile(r"\d+")


def classify_slide_purposes(deck: SlideDeckData) -> list[str]:
    """Map each slide to its spine purpose, or "optional" beyond the spine.

    The first slide resolving to a given spine purpose fills that required
    slot; any later slide with the same (or an unrecognized) purpose is
    optional and counts against the optional-slide budget.
    """
    seen: set[str] = set()
    classified: list[str] = []
    for slide in deck.slides:
        purpose = _slide_purpose_token(slide)
        if purpose in _REQUIRED_SPINE and purpose not in seen:
            seen.add(purpose)
            classified.append(purpose)
        else:
            classified.append("optional")
    return classified


def evaluate_deck_shape(deck: SlideDeckData, teacher_constraints: JsonObject, grade_level: str) -> SlideDeckValidationReport:
    purposes = classify_slide_purposes(deck)
    missing = [purpose for purpose in _REQUIRED_SPINE if purpose not in purposes]
    if missing:
        return _failed(
            "deck_shape_incomplete",
            f"Deck is missing required spine slide(s): {', '.join(missing)}.",
            "deck",
        )
    optional_count = purposes.count("optional")
    budget = _optional_slide_budget(teacher_constraints, grade_level)
    if optional_count > budget:
        return _failed(
            "deck_shape_unjustified_slide",
            "Deck adds optional slides beyond what topic complexity, duration, grade band, or teacher request justifies.",
            "deck",
        )
    return _passed("deck_shape_ok", "Deck keeps the required six-slide spine plus only justified optional slides.", "deck")


def role_density_rule(role: PedagogicalRole | None) -> PurposeDensityRule:
    """Public accessor for a role's density/accessibility budget.

    Lets other modules (e.g. `pedagogical_components.py`, SDTF-07) reuse
    these thresholds instead of duplicating the numbers.
    """
    return _ROLE_DENSITY.get(role, _DEFAULT_DENSITY_RULE) if role else _DEFAULT_DENSITY_RULE


def evaluate_purpose_density(deck: SlideDeckData) -> SlideDeckValidationReport:
    roles = assign_pedagogical_roles(deck)
    for slide, role in zip(deck.slides, roles, strict=True):
        rule = role_density_rule(role)
        role_label = role or "unassigned"
        total_chars = sum(len(block.body) for block in slide.blocks)
        if len(slide.blocks) < rule.min_blocks or total_chars < rule.min_total_chars:
            return _failed(
                "density_purpose_gap",
                f"Slide '{slide.slide_id}' lacks the content its role requires (role={role_label}).",
                "slide",
            )
        if total_chars > rule.max_total_chars:
            return _failed(
                "density_purpose_gap",
                f"Slide '{slide.slide_id}' carries more content than a presentation-ready slide should (role={role_label}).",
                "slide",
            )
        if rule.requires_interaction and not slide.interactions:
            return _failed(
                "density_purpose_gap",
                f"Slide '{slide.slide_id}' is missing the interaction its role requires (role={role_label}).",
                "slide",
            )
    return _passed("density_purpose_ok", "Every slide meets its role-specific density requirements.", "slide")


def assign_pedagogical_roles(deck: SlideDeckData) -> list[PedagogicalRole | None]:
    """Assign each slide a typed pedagogical role, separate from its layout.

    Required spine slides (`classify_slide_purposes`) map 1:1 onto the
    ADR-045 role vocabulary. Optional slides beyond the spine are matched by
    the same slide_id-token convention against a small set of recognized
    extension roles (independent practice, check-understanding, recap);
    anything else is left unassigned (``None``) rather than forced into a
    role it doesn't fit.
    """
    purposes = classify_slide_purposes(deck)
    roles: list[PedagogicalRole | None] = []
    for slide, purpose in zip(deck.slides, purposes, strict=True):
        if purpose in _ROLE_BY_SPINE_PURPOSE:
            roles.append(_ROLE_BY_SPINE_PURPOSE[purpose])
        else:
            roles.append(_OPTIONAL_ROLE_ALIASES.get(_slide_token(slide)))
    return roles


def estimate_slide_planned_minutes(deck: SlideDeckData, teacher_constraints: JsonObject) -> list[float]:
    """Split total lesson time across slides, weighted by pedagogical role.

    `teacher_constraints["duration_minutes"]` (threaded from
    `lesson_plan.duration_minutes` -- see `_optional_slide_budget`) is the
    source of truth for total available time; falls back to a flat
    minutes-per-slide planning default when the teacher hasn't set one.
    """
    roles = assign_pedagogical_roles(deck)
    total_minutes = _total_available_minutes(teacher_constraints, len(deck.slides))
    weights = [_ROLE_PACING_WEIGHT.get(role, _DEFAULT_ROLE_PACING_WEIGHT) if role else _DEFAULT_ROLE_PACING_WEIGHT for role in roles]
    weight_sum = sum(weights) or 1.0
    return [round(total_minutes * weight / weight_sum, 1) for weight in weights]


def annotate_pedagogical_pacing(deck: SlideDeckData, teacher_constraints: JsonObject) -> SlideDeckData:
    """Stamp each slide with its pedagogical role and planned duration.

    Runs once per generated deck (see `SlideDeckEngine.generate`) so
    downstream consumers -- density checks, teacher preview -- can read the
    role/pacing straight off the persisted deck instead of recomputing it
    from `slide_id` conventions or replaying `teacher_constraints`.
    """
    roles = assign_pedagogical_roles(deck)
    minutes = estimate_slide_planned_minutes(deck, teacher_constraints)
    updated_slides = [
        slide.model_copy(update={"pedagogical_role": role, "planned_duration_minutes": slide_minutes})
        for slide, role, slide_minutes in zip(deck.slides, roles, minutes, strict=True)
    ]
    return deck.model_copy(update={"slides": updated_slides})


def _total_available_minutes(teacher_constraints: JsonObject, slide_count: int) -> float:
    duration = teacher_constraints.get("duration_minutes")
    if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration > 0:
        return float(duration)
    return slide_count * _DEFAULT_MINUTES_PER_SLIDE


def _slide_token(slide: SlideDeckSlide) -> str:
    return slide.slide_id.removeprefix("slide-").split("-", 1)[0].lower()


def _slide_purpose_token(slide: SlideDeckSlide) -> str:
    return _PURPOSE_ALIASES.get(_slide_token(slide), "optional")


def _optional_slide_budget(teacher_constraints: JsonObject, grade_level: str) -> int:
    budget = 0
    duration = teacher_constraints.get("duration_minutes")
    if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration >= 45:
        budget += 1
    if teacher_constraints.get("topic_complexity") == "high":
        budget += 1
    grade_number = _grade_number(grade_level)
    if grade_number is not None and grade_number >= 6:
        budget += 1
    requested = teacher_constraints.get("requested_extra_slides")
    if isinstance(requested, (int, float)) and not isinstance(requested, bool) and requested > 0:
        budget += int(requested)
    return budget


def _grade_number(grade_level: str) -> int | None:
    match = _GRADE_NUMBER_RE.search(grade_level)
    return int(match.group()) if match else None


def _failed(code: SlideDeckValidationCode, message: str, scope: SlideDeckHealingScope) -> SlideDeckValidationReport:
    return SlideDeckValidationReport(phase="deck_shape", passed=False, code=code, message=message, scope=scope)


def _passed(code: SlideDeckValidationCode, message: str, scope: SlideDeckHealingScope) -> SlideDeckValidationReport:
    return SlideDeckValidationReport(phase="deck_shape", passed=True, code=code, message=message, scope=scope)
