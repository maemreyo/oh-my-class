from __future__ import annotations

import re
from statistics import mean
from typing import Final

from common.contracts.slide_deck import SlideDeckData

from packages.agents.slide_deck_engine.models import (
    PedagogicalPlan,
    SlideArchitecturePlan,
    SlideDeckHealingReport,
    SlideDeckHealingScope,
    SlideDeckScopedRepairReport,
    SlideDeckScorecard,
    SlideDeckValidationCode,
    SlideDeckValidationReport,
)
from packages.agents.slide_deck_engine.registries import BLOCK_REGISTRY, INTERACTION_REGISTRY, LAYOUT_REGISTRY

_PII_PATTERN: Final = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|\b\d{3}[- .]?\d{3}[- .]?\d{4}\b")
_STACK_TRACE_PATTERN: Final = re.compile(r"Traceback \(most recent call last\)|at \S+\([^)]*\)")
_ANSWER_KEY_PATTERN: Final = re.compile(r"\b(correct answer|answer key|correct_option_ids|acceptable_answers)\b", re.IGNORECASE)
_UNSAFE_RESEARCH_PATTERN: Final = re.compile(r"\b(raw provider|stack trace|untrusted research prose)\b", re.IGNORECASE)


def validate_registry_membership(deck: SlideDeckData) -> list[SlideDeckValidationReport]:
    reports: list[SlideDeckValidationReport] = []
    for slide in deck.slides:
        if slide.layout not in LAYOUT_REGISTRY.entries:
            reports.append(_failed("invalid_layout", "Slide uses a layout missing from the registry.", "slide"))
        for block in slide.blocks:
            if block.block_type not in BLOCK_REGISTRY.entries:
                reports.append(_failed("invalid_block", "Slide block type is missing from the registry.", "block"))
        for interaction in slide.interactions:
            if interaction.interaction_type not in INTERACTION_REGISTRY.entries:
                reports.append(_failed("invalid_interaction", "Slide interaction type is missing from the registry.", "block"))
    if reports:
        return reports
    return [_passed("registry_membership_ok", "All slide layouts, blocks, and interactions are registry-backed.", "deck")]


def validate_pacing(deck: SlideDeckData) -> SlideDeckValidationReport:
    expected_steps = list(range(1, len(deck.slides) + 1))
    actual_steps = [slide.progression.step_index for slide in deck.slides]
    if actual_steps != expected_steps:
        return _failed("pacing_mismatch", "Slide progression step indexes do not match deck order.", "plan")
    return _passed("pacing_ok", "Slide pacing matches deck order.", "plan")


def validate_source_references(deck: SlideDeckData) -> SlideDeckValidationReport:
    source_ids = {source.source_id for source in deck.source_refs}
    for slide in deck.slides:
        for block in slide.blocks:
            if not block.source_ref_ids and block.media is None:
                return _failed("missing_source_refs", "Text block has no source reference.", "block")
            if any(source_ref_id not in source_ids for source_ref_id in block.source_ref_ids):
                return _failed("missing_source_refs", "Block references a source not declared by the deck.", "block")
    return _passed("source_refs_ok", "Deck source references cover textual blocks.", "block")


def validate_objective_coverage(deck: SlideDeckData, plan: PedagogicalPlan) -> SlideDeckValidationReport:
    deck_text = " ".join([deck.title, *(slide.title for slide in deck.slides), *(block.body for slide in deck.slides for block in slide.blocks)]).lower()
    goal_terms = [term for term in re.findall(r"[a-zA-Z]{4,}", plan.learning_goal.lower()) if term not in {"students", "will", "lesson", "goal"}]
    if not goal_terms or not any(term in deck_text for term in goal_terms):
        return _failed("objective_coverage_gap", "Deck text does not cover the planned learning objective.", "plan")
    return _passed("objective_coverage_ok", "Deck text covers the planned learning objective.", "plan")


def validate_media_support(deck: SlideDeckData) -> SlideDeckValidationReport:
    for slide in deck.slides:
        for block in slide.blocks:
            media = block.media
            if media is None:
                continue
            if media.tier == "packaged" and media.requires_network:
                return _failed("unsupported_media", "Packaged media must not require network access.", "block")
            if media.tier == "online_optional" and not deck.media_policy.online_optional_allowed:
                return _failed("unsupported_media", "Online optional media is disabled by deck media policy.", "block")
    return _passed("html_exports_ready", "Media choices are compatible with standalone HTML export.", "deck")


def validate_teacher_only_separation(deck: SlideDeckData) -> SlideDeckValidationReport:
    for slide in deck.slides:
        for interaction in slide.interactions:
            if interaction.answer_bearing and interaction.teacher_only is None:
                return _failed("teacher_only_leak_risk", "Answer-bearing interaction lacks teacher-only separation.", "block")
    return _passed("teacher_only_separation_ok", "Answer-bearing interactions use teacher-only projection.", "block")


def build_healing_reports(validations: list[SlideDeckValidationReport]) -> list[SlideDeckHealingReport]:
    failures = [report for report in validations if not report.passed]
    if not failures:
        return [SlideDeckHealingReport()]
    return [_healing_for(report) for report in failures]


def build_scorecard(validations: list[SlideDeckValidationReport], deck: SlideDeckData) -> SlideDeckScorecard:
    density = _score(validations, {"density_budget_ok", "density_budget_exceeded"})
    accessibility = _score(validations, {"accessibility_ok", "missing_alt_text"})
    surface = _score(validations, {"surfaces_ready", "teacher_only_separation_ok", "teacher_only_leak_risk"})
    objective = _score(validations, {"objective_coverage_ok", "objective_coverage_gap"})
    pacing = _score(validations, {"pacing_ok", "pacing_mismatch", "page_count_ok", "page_count_too_short", "page_count_exceeded"})
    interaction = _score(validations, {"invalid_interaction", "teacher_only_separation_ok", "teacher_only_leak_risk"})
    source = _score(validations, {"source_refs_ok", "missing_source_refs"})
    offline = _offline_score(deck)
    variety = min(1.0, len({slide.layout for slide in deck.slides}) / 2)
    dimensions = [density, accessibility, surface, objective, pacing, variety, interaction, offline, source]
    return SlideDeckScorecard(
        overall_score=round(mean(dimensions), 3),
        density_score=density,
        accessibility_score=accessibility,
        surface_score=surface,
        objective_coverage_score=objective,
        pacing_fit_score=pacing,
        visual_variety_score=variety,
        interaction_appropriateness_score=interaction,
        teacher_only_separation_score=_score(validations, {"teacher_only_separation_ok", "teacher_only_leak_risk"}),
        offline_readiness_score=offline,
        source_reference_score=source,
    )


def trace_artifacts(
    deck: SlideDeckData,
    architecture: SlideArchitecturePlan,
    validations: list[SlideDeckValidationReport],
    healing_reports: list[SlideDeckHealingReport],
    scorecard: SlideDeckScorecard,
    scoped_repair: SlideDeckScopedRepairReport,
) -> tuple[dict[str, str | int | list[str]], dict[str, str | int], dict[str, list[dict[str, str | bool]]], dict[str, list[dict[str, str | bool | None]]], dict[str, float], dict[str, str], dict[str, str | int | float], dict[str, str | bool | int], dict[str, str | bool | list[str]]]:
    plan_artifact = {
        "slide_count": len(architecture.slide_titles),
        "slide_titles": [_redact_text(title) for title in architecture.slide_titles],
        "layouts": list(architecture.layouts),
    }
    data_artifact = {"deck_id": deck.deck_id, "title": _redact_text(deck.title), "slide_count": len(deck.slides)}
    validation_artifact = {"reports": [{"phase": report.phase, "passed": report.passed, "code": report.code, "scope": report.scope} for report in validations]}
    healing_artifact = {"reports": [{"attempted": report.attempted, "failure_code": report.failure_code, "scope": report.scope, "strategy": report.strategy, "outcome": report.outcome, "final_status": report.final_status} for report in healing_reports]}
    scorecard_artifact = scorecard.model_dump(mode="json")
    source_ref_map = {source.source_id: _redact_text(source.citation) for source in deck.source_refs}
    model_cost_metadata = {"llm_calls": 0, "estimated_cost_usd": 0.0, "provider": "none"}
    export_readiness_manifest = {"format": "html", "student": True, "teacher": True, "print": True, "slide_count": len(deck.slides)}
    scoped_regeneration_artifact = scoped_repair.model_dump(mode="json")
    return (
        plan_artifact,
        data_artifact,
        validation_artifact,
        healing_artifact,
        scorecard_artifact,
        source_ref_map,
        model_cost_metadata,
        export_readiness_manifest,
        scoped_regeneration_artifact,
    )


def _healing_for(report: SlideDeckValidationReport) -> SlideDeckHealingReport:
    match report.code:
        case "density_budget_exceeded" | "missing_alt_text" | "invalid_block" | "missing_source_refs" | "teacher_only_leak_risk" | "unsupported_media":
            strategy = "rewrite"
            scope = report.scope
        case "invalid_layout" | "invalid_interaction" | "pacing_mismatch" | "objective_coverage_gap":
            strategy = "replan"
            scope = report.scope
        case "page_count_too_short" | "page_count_exceeded" | "html_exports_incomplete":
            strategy = "replan"
            scope = "deck"
        case "accessibility_ok" | "density_budget_ok" | "html_exports_ready" | "objective_coverage_ok" | "pacing_ok" | "page_count_ok" | "registry_membership_ok" | "source_refs_ok" | "surfaces_ready" | "teacher_only_separation_ok":
            strategy = "none"
            scope = "none"
        case "surfaces_incomplete":
            strategy = "replan"
            scope = "deck"
        case unreachable:
            from typing import assert_never

            assert_never(unreachable)
    return SlideDeckHealingReport(
        attempted=strategy != "none",
        failure_code=report.code,
        scope=scope,
        strategy=strategy,
        outcome="planned" if strategy != "none" else "not_needed",
        final_status="failed" if strategy != "none" else "not_applicable",
        message=f"{scope}-scoped {strategy} planned for {report.code}.",
    )


def _score(validations: list[SlideDeckValidationReport], codes: set[SlideDeckValidationCode]) -> float:
    relevant = [report for report in validations if report.code in codes]
    if not relevant:
        return 1.0
    return 1.0 if all(report.passed for report in relevant) else 0.0


def _offline_score(deck: SlideDeckData) -> float:
    media_items = [block.media for slide in deck.slides for block in slide.blocks if block.media is not None]
    if not media_items:
        return 1.0
    return 0.0 if any(media.requires_network and not media.fallback_text for media in media_items) else 1.0


def _failed(code: SlideDeckValidationCode, message: str, scope: SlideDeckHealingScope) -> SlideDeckValidationReport:
    return SlideDeckValidationReport(phase="engine_quality", passed=False, code=code, message=message, scope=scope)


def _passed(code: SlideDeckValidationCode, message: str, scope: SlideDeckHealingScope) -> SlideDeckValidationReport:
    return SlideDeckValidationReport(phase="engine_quality", passed=True, code=code, message=message, scope=scope)


def _redact_text(value: str) -> str:
    return redact_trace_text(value)


def redact_trace_text(value: str) -> str:
    redacted = _PII_PATTERN.sub("[redacted]", value)
    redacted = _STACK_TRACE_PATTERN.sub("[redacted]", redacted)
    redacted = _ANSWER_KEY_PATTERN.sub("[redacted]", redacted)
    return _UNSAFE_RESEARCH_PATTERN.sub("[redacted]", redacted)
