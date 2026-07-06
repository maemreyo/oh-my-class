from __future__ import annotations

from common.contracts.slide_deck import SlideDeckData
from packages.agents.slide_deck_engine.models import SlideDeckValidationReport


def check_export_readiness(deck: SlideDeckData) -> SlideDeckValidationReport:
    exports_html = all(
        surface.export_format == "html"
        for surface in (deck.surfaces.student, deck.surfaces.teacher, deck.surfaces.print)
    )
    return SlideDeckValidationReport(
        phase="export_readiness",
        passed=exports_html,
        code="html_exports_ready" if exports_html else "html_exports_incomplete",
        message="Phase 1 standalone HTML export declarations are present.",
        scope="deck",
    )
