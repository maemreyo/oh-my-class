"""RCM Component Registry — machine-readable catalog of UI content components.

Single source of truth for which components exist, which artifacts they
belong to, cardinality constraints, required fields, and templates.
"""
from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field


class PedagogicalIntent(StrEnum):
    """Semantic role a component plays inside a teaching artifact."""

    STRUCTURAL = "structural"
    DATA_DISPLAY = "data_display"
    TIMELINE_FLOW = "timeline_flow"
    ASSESSMENT = "assessment"
    KNOWLEDGE_ORGANIZATION = "knowledge_organization"
    MEDIA_ACTIVITY = "media_activity"
    RECALL = "recall"
    ADMINISTRATIVE = "administrative"


class ComponentEntry(BaseModel):
    """Immutable metadata for a single content component type."""

    model_config = ConfigDict(frozen=True)

    type: str
    intent: PedagogicalIntent
    artifact_types: frozenset[str] = Field(default_factory=frozenset)
    min_per_artifact: int = 0
    max_per_artifact: int | None = None
    required_fields: tuple[str, ...] = ()
    template: str | None = None
    description: str = ""


_DISPATCHER_DIR = Path(
    "packages/renderer/templates/components"
)

# Component types whose dispatcher template file name differs from the type.
_TEMPLATE_FILE_OVERRIDES: Final[dict[str, str]] = {
    "film_clip_activity": "film_card.html",
    "phrasal_verb_cluster": "phrasal_clusters.html",
    "vocab_cluster": "vocab_concept_box.html",
}


def _template_exists(component_type: str) -> str | None:
    """Return the template filename if it exists on disk, else None.

    Uses ``_TEMPLATE_FILE_OVERRIDES`` for types whose dispatcher filename
    does not match ``{type}.html``.
    """
    filename = _TEMPLATE_FILE_OVERRIDES.get(
        component_type, f"{component_type}.html"
    )
    if (_DISPATCHER_DIR / filename).exists():
        return filename
    return None


# ---------------------------------------------------------------------------
# Registry entries
# ---------------------------------------------------------------------------

_ENTRIES: tuple[ComponentEntry, ...] = (
    # ── Structural ────────────────────────────────────────────────────────
    ComponentEntry(
        type="heading",
        intent=PedagogicalIntent.STRUCTURAL,
        artifact_types=frozenset({
            "lesson", "worksheet", "quiz", "drill", "recap", "infographic",
        }),
        min_per_artifact=1,
        max_per_artifact=None,
        required_fields=("level", "text"),
        template=_template_exists("heading"),
        description="Section heading with level 1–4.",
    ),
    ComponentEntry(
        type="paragraph",
        intent=PedagogicalIntent.STRUCTURAL,
        artifact_types=frozenset({
            "lesson", "worksheet", "recap", "infographic",
        }),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("text",),
        template=_template_exists("paragraph"),
        description="Free-text paragraph.",
    ),
    ComponentEntry(
        type="callout",
        intent=PedagogicalIntent.STRUCTURAL,
        artifact_types=frozenset({
            "lesson", "worksheet", "drill", "recap",
        }),
        min_per_artifact=0,
        max_per_artifact=3,
        required_fields=("variant", "body"),
        template=_template_exists("callout"),
        description="Note/warning/tip callout box.",
    ),
    ComponentEntry(
        type="ordered_list",
        intent=PedagogicalIntent.STRUCTURAL,
        artifact_types=frozenset({"lesson", "worksheet", "recap"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("items",),
        template=_template_exists("ordered_list"),
        description="Numbered step-by-step list.",
    ),
    ComponentEntry(
        type="unordered_list",
        intent=PedagogicalIntent.STRUCTURAL,
        artifact_types=frozenset({"lesson", "worksheet", "recap"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("items",),
        template=_template_exists("unordered_list"),
        description="Bulleted list.",
    ),
    # ── Data display ──────────────────────────────────────────────────────
    ComponentEntry(
        type="table",
        intent=PedagogicalIntent.DATA_DISPLAY,
        artifact_types=frozenset({
            "lesson", "worksheet", "quiz", "drill", "recap", "infographic",
        }),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("columns", "rows"),
        template=_template_exists("table"),
        description="Tabular data with columns and rows.",
    ),
    ComponentEntry(
        type="stat_grid",
        intent=PedagogicalIntent.DATA_DISPLAY,
        artifact_types=frozenset({
            "lesson", "recap", "infographic",
        }),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("stats",),
        template=_template_exists("stat_grid"),
        description="Grid of statistic cards.",
    ),
    ComponentEntry(
        type="pattern_grid",
        intent=PedagogicalIntent.DATA_DISPLAY,
        artifact_types=frozenset({"lesson", "worksheet"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("patterns",),
        template=_template_exists("pattern_grid"),
        description="Grid of pattern cards.",
    ),
    ComponentEntry(
        type="trait_grid",
        intent=PedagogicalIntent.DATA_DISPLAY,
        artifact_types=frozenset({"lesson", "infographic"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("traits",),
        template=_template_exists("trait_grid"),
        description="Grid of trait/characteristic cards.",
    ),
    ComponentEntry(
        type="taxonomy_grid",
        intent=PedagogicalIntent.DATA_DISPLAY,
        artifact_types=frozenset({"lesson", "infographic"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("items",),
        template=_template_exists("taxonomy_grid"),
        description="Grid of taxonomy/classification items.",
    ),
    # ── Timeline / flow ───────────────────────────────────────────────────
    ComponentEntry(
        type="phase_timeline",
        intent=PedagogicalIntent.TIMELINE_FLOW,
        artifact_types=frozenset({"lesson"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("phases",),
        template=_template_exists("phase_timeline"),
        description="Multi-phase roadmap timeline.",
    ),
    ComponentEntry(
        type="flow_step",
        intent=PedagogicalIntent.TIMELINE_FLOW,
        artifact_types=frozenset({"lesson", "worksheet"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("steps",),
        template=_template_exists("flow_step"),
        description="Sequential flow steps with time markers.",
    ),
    ComponentEntry(
        type="timeline",
        intent=PedagogicalIntent.TIMELINE_FLOW,
        artifact_types=frozenset({"lesson", "infographic"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("events",),
        template=_template_exists("timeline"),
        description="Chronological event timeline.",
    ),
    # ── Assessment ────────────────────────────────────────────────────────
    ComponentEntry(
        type="question_card",
        intent=PedagogicalIntent.ASSESSMENT,
        artifact_types=frozenset({
            "lesson", "quiz", "drill", "worksheet", "recap",
        }),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("id", "text", "options", "answer", "explain"),
        template=_template_exists("question_card"),
        description="Single multiple-choice question card.",
    ),
    ComponentEntry(
        type="question_list",
        intent=PedagogicalIntent.ASSESSMENT,
        artifact_types=frozenset({"lesson", "quiz", "drill", "worksheet"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("questions",),
        template=_template_exists("question_list"),
        description="Grouped list of question cards.",
    ),
    # ── Knowledge organization ────────────────────────────────────────────
    ComponentEntry(
        type="concept_map",
        intent=PedagogicalIntent.KNOWLEDGE_ORGANIZATION,
        artifact_types=frozenset({"lesson"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("nodes",),
        template=_template_exists("concept_map"),
        description="Concept relationship map.",
    ),
    ComponentEntry(
        type="vocab_cluster",
        intent=PedagogicalIntent.KNOWLEDGE_ORGANIZATION,
        artifact_types=frozenset({"lesson", "worksheet", "drill"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("title",),
        template=_template_exists("vocab_cluster"),
        description="Vocabulary cluster with discriminations.",
    ),
    ComponentEntry(
        type="contrastive_pairs",
        intent=PedagogicalIntent.KNOWLEDGE_ORGANIZATION,
        artifact_types=frozenset({"lesson", "worksheet"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("rows",),
        template=_template_exists("contrastive_pairs"),
        description="Side-by-side contrastive pairs.",
    ),
    ComponentEntry(
        type="phrasal_verb_cluster",
        intent=PedagogicalIntent.KNOWLEDGE_ORGANIZATION,
        artifact_types=frozenset({"lesson", "worksheet"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("groups",),
        template=_template_exists("phrasal_verb_cluster"),
        description="Phrasal verb grouped clusters.",
    ),
    # ── Media / activity ──────────────────────────────────────────────────
    ComponentEntry(
        type="film_clip_activity",
        intent=PedagogicalIntent.MEDIA_ACTIVITY,
        artifact_types=frozenset({"lesson"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("clips",),
        template=_template_exists("film_clip_activity"),
        description="Film clip viewing activity.",
    ),
    ComponentEntry(
        type="roleplay_script",
        intent=PedagogicalIntent.MEDIA_ACTIVITY,
        artifact_types=frozenset({"lesson"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("lines",),
        template=_template_exists("roleplay_script"),
        description="Roleplay dialogue script.",
    ),
    # ── Recall ────────────────────────────────────────────────────────────
    ComponentEntry(
        type="active_recall_prompt",
        intent=PedagogicalIntent.RECALL,
        artifact_types=frozenset({"lesson", "recap"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("instruction",),
        template=_template_exists("active_recall_prompt"),
        description="Active recall self-testing prompt.",
    ),
    # ── Administrative ────────────────────────────────────────────────────
    ComponentEntry(
        type="hw_list",
        intent=PedagogicalIntent.ADMINISTRATIVE,
        artifact_types=frozenset({"lesson"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("items",),
        template=_template_exists("hw_list"),
        description="Homework assignment list.",
    ),
    ComponentEntry(
        type="alert",
        intent=PedagogicalIntent.ADMINISTRATIVE,
        artifact_types=frozenset({"lesson", "worksheet"}),
        min_per_artifact=0,
        max_per_artifact=None,
        required_fields=("body",),
        template=_template_exists("alert"),
        description="Inline alert/banner message.",
    ),
)

# Public constants
COMPONENT_REGISTRY: Final[tuple[ComponentEntry, ...]] = _ENTRIES

_ENTRY_BY_TYPE: Final[dict[str, ComponentEntry]] = {
    e.type: e for e in _ENTRIES
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_entry(component_type: str) -> ComponentEntry:
    """Return registry entry for *component_type* or raise ``KeyError``."""
    try:
        return _ENTRY_BY_TYPE[component_type]
    except KeyError:
        available = ", ".join(sorted(_ENTRY_BY_TYPE))
        raise KeyError(
            f"Unknown component type {component_type!r}. "
            f"Available: {available}"
        ) from None


def get_entries_for_artifact(artifact_type: str) -> list[ComponentEntry]:
    """Return all entries whose *artifact_types* include *artifact_type*."""
    return [e for e in _ENTRIES if artifact_type in e.artifact_types]


def get_minimum_components(artifact_type: str) -> dict[str, int]:
    """Return ``{type: min}`` for components required by *artifact_type*.

    Only entries with ``min_per_artifact > 0`` are included.
    """
    return {
        e.type: e.min_per_artifact
        for e in _ENTRIES
        if artifact_type in e.artifact_types and e.min_per_artifact > 0
    }


def get_component_types_for_intent(intent: PedagogicalIntent) -> list[str]:
    """Return sorted list of component type names for *intent*."""
    return sorted(e.type for e in _ENTRIES if e.intent == intent)
