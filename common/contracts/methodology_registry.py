from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, assert_never

CompatibilityStatus = Literal["compatible", "conflict", "neutral"]
RequirementMode = Literal["any", "all"]

METHODOLOGY_TAG_VALUES: Final = (
    "concept_map",
    "contrastive_pairs",
    "film_based",
    "shy_student_1on1",
    "active_recall",
    "why_wrong_reasoning",
    "timed_quiz",
    "roleplay_script",
    "inverse_thinking",
)

MethodologyTag = Literal[*METHODOLOGY_TAG_VALUES]


@dataclass(frozen=True, slots=True)
class MethodologyRegistryEntry:
    tag: MethodologyTag
    label_en: str
    label_vi: str
    description: str
    required_components: tuple[str, ...]
    requirement_mode: RequirementMode
    supported_artifacts: tuple[str, ...]
    export_formats: tuple[str, ...]
    conflicts: tuple[MethodologyTag, ...] = ()
    compatible_with: tuple[MethodologyTag, ...] = ()


@dataclass(frozen=True, slots=True)
class MethodologyPairRule:
    left: MethodologyTag
    right: MethodologyTag
    status: CompatibilityStatus
    rationale: str


@dataclass(frozen=True, slots=True)
class CompositeProjectionPlan:
    ordered_tags: tuple[MethodologyTag, ...]
    required_components: tuple[str, ...]
    source_methodology_tags: dict[str, tuple[MethodologyTag, ...]]


METHODOLOGY_REGISTRY: Final[tuple[MethodologyRegistryEntry, ...]] = (
    MethodologyRegistryEntry(
        tag="concept_map",
        label_en="Concept Map",
        label_vi="Sơ đồ khái niệm",
        description="Organize ideas as connected concepts for relationship-first learning.",
        required_components=("vocab_cluster", "contrastive_pairs"),
        requirement_mode="any",
        supported_artifacts=("lesson", "worksheet", "recap"),
        export_formats=("html", "h5p"),
        compatible_with=("contrastive_pairs", "active_recall"),
    ),
    MethodologyRegistryEntry(
        tag="contrastive_pairs",
        label_en="Contrastive Pairs",
        label_vi="Cặp đối chiếu",
        description="Teach close concepts by comparing their boundaries and examples.",
        required_components=("contrastive_pairs",),
        requirement_mode="all",
        supported_artifacts=("lesson", "worksheet", "recap"),
        export_formats=("html", "h5p"),
        compatible_with=("concept_map", "why_wrong_reasoning"),
    ),
    MethodologyRegistryEntry(
        tag="film_based",
        label_en="Film Based",
        label_vi="Học qua phim",
        description="Anchor learning in short clips, viewing tasks, and post-viewing synthesis.",
        required_components=("film_clip_activity",),
        requirement_mode="all",
        supported_artifacts=("lesson", "worksheet"),
        export_formats=("html",),
    ),
    MethodologyRegistryEntry(
        tag="shy_student_1on1",
        label_en="Shy Student 1:1",
        label_vi="Học 1:1 cho học sinh rụt rè",
        description="Use low-pressure scripts and private practice for hesitant learners.",
        required_components=("roleplay_script",),
        requirement_mode="all",
        supported_artifacts=("lesson", "worksheet"),
        export_formats=("html",),
        conflicts=("timed_quiz",),
        compatible_with=("roleplay_script",),
    ),
    MethodologyRegistryEntry(
        tag="active_recall",
        label_en="Active Recall",
        label_vi="Gợi nhớ chủ động",
        description="Prompt retrieval before explanation so students strengthen memory pathways.",
        required_components=("active_recall_prompt",),
        requirement_mode="all",
        supported_artifacts=("lesson", "worksheet", "quiz", "drill", "recap"),
        export_formats=("html", "gift", "h5p"),
        compatible_with=("concept_map", "timed_quiz", "inverse_thinking"),
    ),
    MethodologyRegistryEntry(
        tag="why_wrong_reasoning",
        label_en="Why Wrong Reasoning",
        label_vi="Vì sao sai",
        description="Explain distractors and wrong paths so misconceptions become visible.",
        required_components=("wrong_reasons",),
        requirement_mode="all",
        supported_artifacts=("lesson", "worksheet", "quiz", "drill", "recap"),
        export_formats=("html", "gift", "h5p"),
        compatible_with=("contrastive_pairs",),
    ),
    MethodologyRegistryEntry(
        tag="timed_quiz",
        label_en="Timed Quiz",
        label_vi="Bài kiểm tra tính giờ",
        description="Add time-boxed practice while preserving accessibility and feedback.",
        required_components=("time_limit",),
        requirement_mode="all",
        supported_artifacts=("quiz", "drill"),
        export_formats=("html", "gift", "h5p"),
        compatible_with=("active_recall",),
    ),
    MethodologyRegistryEntry(
        tag="roleplay_script",
        label_en="Roleplay Script",
        label_vi="Kịch bản đóng vai",
        description="Give students structured dialogue practice with separated teacher notes.",
        required_components=("roleplay_script",),
        requirement_mode="all",
        supported_artifacts=("lesson", "worksheet"),
        export_formats=("html",),
        conflicts=("timed_quiz",),
        compatible_with=("shy_student_1on1",),
    ),
    MethodologyRegistryEntry(
        tag="inverse_thinking",
        label_en="Inverse Thinking",
        label_vi="Tư duy ngược",
        description="Start from a disaster, inspect clues, define the safe zone, and file the rule.",
        required_components=("case_flow", "summary_table"),
        requirement_mode="all",
        supported_artifacts=("lesson", "worksheet", "quiz", "recap"),
        export_formats=("html", "gift", "h5p"),
        compatible_with=("active_recall",),
    ),
)


def methodology_entry_by_tag(tag: MethodologyTag) -> MethodologyRegistryEntry:
    for entry in METHODOLOGY_REGISTRY:
        if entry.tag == tag:
            return entry
    assert_never(tag)


def compatibility_for(left: MethodologyTag, right: MethodologyTag) -> CompatibilityStatus:
    left_entry = methodology_entry_by_tag(left)
    right_entry = methodology_entry_by_tag(right)
    if left == right or right in left_entry.compatible_with or left in right_entry.compatible_with:
        return "compatible"
    if right in left_entry.conflicts or left in right_entry.conflicts:
        return "conflict"
    return "neutral"


def pair_rule_for(left: MethodologyTag, right: MethodologyTag) -> MethodologyPairRule:
    status = compatibility_for(left, right)
    return MethodologyPairRule(
        left=left,
        right=right,
        status=status,
        rationale=_pair_rationale(left, right, status),
    )


def all_pair_rules() -> tuple[MethodologyPairRule, ...]:
    return tuple(pair_rule_for(left, right) for left in METHODOLOGY_TAG_VALUES for right in METHODOLOGY_TAG_VALUES)


def build_composite_projection_plan(tags: list[MethodologyTag]) -> CompositeProjectionPlan:
    ordered_tags = tuple(tag for tag in METHODOLOGY_TAG_VALUES if tag in tags)
    required_components: list[str] = []
    sources: dict[str, list[MethodologyTag]] = {}
    for tag in ordered_tags:
        entry = methodology_entry_by_tag(tag)
        for component in entry.required_components:
            if component not in required_components:
                required_components.append(component)
            sources.setdefault(component, []).append(tag)
    return CompositeProjectionPlan(
        ordered_tags=ordered_tags,
        required_components=tuple(required_components),
        source_methodology_tags={component: tuple(source_tags) for component, source_tags in sources.items()},
    )


def _pair_rationale(left: MethodologyTag, right: MethodologyTag, status: CompatibilityStatus) -> str:
    if left == right:
        return "Same methodology selected once."
    match status:
        case "compatible":
            return f"{left} and {right} can share one composite projection without hiding required practice."
        case "conflict":
            return f"{left} and {right} conflict because timed public pressure does not fit private rehearsal flows."
        case "neutral":
            return f"{left} and {right} have no explicit composite projection; keep them separate until classified."
        case unreachable:
            assert_never(unreachable)
