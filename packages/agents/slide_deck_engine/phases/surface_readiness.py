from __future__ import annotations

from common.contracts.slide_deck import SlideDeckData

from packages.agents.slide_deck_engine.models import SlideDeckValidationReport


def check_surface_readiness(deck: SlideDeckData) -> SlideDeckValidationReport:
    ready = (
        deck.surfaces.student.mode == "presentation"
        and deck.surfaces.teacher.mode == "teacher_guide"
        and deck.surfaces.print.mode == "print"
    )
    return SlideDeckValidationReport(
        phase="surface_readiness",
        passed=ready,
        code="surfaces_ready" if ready else "surfaces_incomplete",
        message="Student, teacher, and print surfaces are declared.",
        scope="deck",
    )
