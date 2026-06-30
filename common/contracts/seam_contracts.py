from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class PlannerHandoff(BaseModel):
    """Contract: planning_blueprint → post_blueprint_research seam.

    Fail-closed: raises ValidationError if planner output is missing required
    fields that researcher depends on. Never silently degrades.
    """

    lesson_plan: dict = Field(description="Planner output; researcher reads topic + objectives")

    @model_validator(mode="after")
    def check_required_fields(self) -> "PlannerHandoff":
        plan = self.lesson_plan
        if not plan.get("topic"):
            raise ValueError("lesson_plan.topic is required at planning_blueprint seam")
        objectives = plan.get("learning_objectives")
        if not objectives or not isinstance(objectives, list):
            raise ValueError(
                "lesson_plan.learning_objectives must be a non-empty list "
                "at planning_blueprint seam"
            )
        return self


class ResearcherHandoff(BaseModel):
    """Contract: post_blueprint_research → artifact_workflow seam.

    Validates that the researcher produced usable research_brief and that
    lesson_plan persists intact for content_creator.
    """

    lesson_plan: dict
    research_brief: dict = Field(description="Researcher output; content_creator reads sources")

    @model_validator(mode="after")
    def check_required_fields(self) -> "ResearcherHandoff":
        sources = self.research_brief.get("sources")
        if not sources or not isinstance(sources, list) or len(sources) == 0:
            raise ValueError(
                "research_brief.sources must be a non-empty list "
                "at post_blueprint_research seam"
            )
        if not self.lesson_plan.get("topic"):
            raise ValueError(
                "lesson_plan.topic must be present at post_blueprint_research seam"
            )
        return self


class ArtifactWorkflowHandoff(BaseModel):
    """Contract: artifact_workflow → render_quality seam.

    Validates that content_creator produced at least one identifiable artifact
    before render_quality tries to render them.
    """

    artifacts: list[dict] = Field(
        description="Content creator output; render_quality reads artifact_id and content",
    )

    @model_validator(mode="after")
    def check_artifacts(self) -> "ArtifactWorkflowHandoff":
        if not self.artifacts:
            raise ValueError(
                "artifacts is empty at artifact_workflow seam — "
                "content_creator must produce at least one artifact"
            )
        for i, artifact in enumerate(self.artifacts):
            if not artifact.get("artifact_id") and not artifact.get("id"):
                raise ValueError(
                    f"artifacts[{i}] is missing artifact_id at artifact_workflow seam"
                )
        return self
