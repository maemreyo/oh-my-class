from __future__ import annotations

from dataclasses import dataclass

from packages.agents.config.models import ModelAssignments


@dataclass(frozen=True, slots=True)
class ModelSnapshot:
    config_version: str
    assignments: dict[str, str]


@dataclass(frozen=True, slots=True)
class DriftDecision:
    changed: bool
    alert: str | None
    generation_model: str | None


def snapshot_models(models: ModelAssignments, *, config_version: str = "models.v1") -> ModelSnapshot:
    return ModelSnapshot(
        config_version=config_version,
        assignments={
            "lead_agent": models.lead_agent,
            "planner": models.planner,
            "researcher": models.researcher,
            "content_creator": models.content_creator,
            "reviewer": models.reviewer,
            "diagnostician": models.diagnostician,
            "llm_judge": models.llm_judge,
            "fact_verification": models.fact_verification,
            "quality_gate": models.quality_gate,
            "blueprint_design": models.blueprint_design,
            "content_generation": models.content_generation,
            "schema_rewrite": models.schema_rewrite,
            "summarization": models.summarization,
            "title_generation": models.title_generation,
            "content_review_light": models.content_review_light,
        },
    )


def evaluate_model_drift(
    previous: ModelSnapshot,
    current: ModelSnapshot,
    *,
    golden_score_delta: float,
) -> DriftDecision:
    changed = previous != current
    if changed and golden_score_delta < -0.02:
        return DriftDecision(
            changed=True,
            alert="model_snapshot_regression",
            generation_model=previous.assignments["content_generation"],
        )
    return DriftDecision(changed=changed, alert="model_snapshot_changed" if changed else None, generation_model=None)
