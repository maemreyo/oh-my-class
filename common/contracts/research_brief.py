from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ResearchRiskLevel = Literal["low", "medium", "high"]
ResearchPolicy = Literal["basic", "standard", "rigorous"]


class EvidenceCitation(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=2000)
    domain: str = Field(min_length=1, max_length=255)
    credibility_score: float = Field(ge=0.0, le=1.0)


class ArtifactResearchGuidance(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_type: str = Field(min_length=1, max_length=64)
    guidance: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)


class PrePlanningSearchBrief(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=80)
    risk_level: ResearchRiskLevel
    query_count: int = Field(ge=0, le=20)
    confirmation_reasons: tuple[str, ...] = ()


class ResearchBrief(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=80)
    key_findings: list[str] = Field(default_factory=list)
    citations: list[EvidenceCitation] = Field(default_factory=list)
    artifact_guidance: list[ArtifactResearchGuidance] = Field(default_factory=list)
    research_policy: ResearchPolicy = "standard"
