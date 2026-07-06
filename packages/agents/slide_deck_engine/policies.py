from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.slide_deck import SlideDeckData

from packages.agents.slide_deck_engine.models import SlideDeckValidationReport


class PageCountPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_slides: int = Field(ge=1)
    max_slides: int = Field(ge=1)

    def evaluate(self, deck: SlideDeckData) -> SlideDeckValidationReport:
        slide_count = len(deck.slides)
        if slide_count < self.min_slides:
            return SlideDeckValidationReport(
                phase="page_count",
                passed=False,
                code="page_count_too_short",
                message="Slide deck has fewer slides than the page-count policy allows.",
                scope="deck",
            )
        if slide_count > self.max_slides:
            return SlideDeckValidationReport(
                phase="page_count",
                passed=False,
                code="page_count_exceeded",
                message="Slide deck has more slides than the page-count policy allows.",
                scope="deck",
            )
        return SlideDeckValidationReport(
            phase="page_count",
            passed=True,
            code="page_count_ok",
            message="Slide count is within policy.",
            scope="deck",
        )


class DensityBudgetPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_blocks_per_slide: int = Field(ge=1)
    max_interactions_per_slide: int = Field(ge=0)

    def evaluate(self, deck: SlideDeckData) -> SlideDeckValidationReport:
        for slide in deck.slides:
            if len(slide.blocks) > self.max_blocks_per_slide:
                return self._failed()
            if len(slide.interactions) > self.max_interactions_per_slide:
                return self._failed()
        return SlideDeckValidationReport(
            phase="density_budget",
            passed=True,
            code="density_budget_ok",
            message="Slide density is within policy.",
            scope="slide",
        )

    def _failed(self) -> SlideDeckValidationReport:
        return SlideDeckValidationReport(
            phase="density_budget",
            passed=False,
            code="density_budget_exceeded",
            message="A slide exceeds the configured density budget.",
            scope="slide",
        )
