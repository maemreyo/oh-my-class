from __future__ import annotations

from common.contracts.slide_deck import SlideDeckData

from packages.agents.slide_deck_engine.models import SlideDeckValidationReport
from packages.agents.slide_deck_engine.policies import DensityBudgetPolicy, PageCountPolicy


def audit_density_and_accessibility(deck: SlideDeckData) -> list[SlideDeckValidationReport]:
    alt_text_report = _check_alt_text(deck)
    return [
        PageCountPolicy(min_slides=1, max_slides=12).evaluate(deck),
        DensityBudgetPolicy(max_blocks_per_slide=4, max_interactions_per_slide=2).evaluate(deck),
        alt_text_report,
    ]


def _check_alt_text(deck: SlideDeckData) -> SlideDeckValidationReport:
    for slide in deck.slides:
        for block in slide.blocks:
            if block.media is not None and not block.media.alt_text.strip():
                return SlideDeckValidationReport(
                    phase="accessibility",
                    passed=False,
                    code="missing_alt_text",
                    message="Media block is missing required alt text.",
                    scope="block",
                )
    return SlideDeckValidationReport(
        phase="accessibility",
        passed=deck.accessibility.alt_text_required and deck.accessibility.keyboard_navigation,
        code="accessibility_ok",
        message="Accessibility metadata is present for the deterministic deck.",
        scope="block",
    )
