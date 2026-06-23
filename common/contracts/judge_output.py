"""Judge output Pydantic models — output contract for the Reviewer Agent (LLM-as-Judge).

Defines the schema for G-Eval scoring results across the 3 quality layers
(format compliance, content quality, presentation).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LayerScore(BaseModel):
    """Score for a single quality layer in the G-Eval framework."""

    layer: str = Field(
        ...,
        description="Layer name: 'format_compliance', 'content_quality', or 'presentation'",
    )
    score: float = Field(..., ge=0, le=10)
    weight: float = Field(
        ...,
        ge=0,
        le=1,
        description="Weight for this layer in the overall score (must sum to 1.0)",
    )
    issues: list[str] = Field(default_factory=list)


class JudgeOutput(BaseModel):
    """Final judgment output from the Reviewer Agent.

    Produced by 3 independent judge calls; majority vote determines the final score.
    Pass threshold: overall_score >= 7.0 AND no critical issues.
    """

    overall_score: float = Field(..., ge=0, le=10)
    layer_scores: list[LayerScore] = Field(default_factory=list)
    critical_issues: list[str] = Field(
        default_factory=list,
        description="Issues that auto-fail regardless of score",
    )
    passed: bool = Field(
        ...,
        description="True if overall_score >= 7.0 and no critical issues",
    )
    rationale: str = Field(
        ...,
        min_length=1,
        description="Think-before-score rationale (written before numeric scores)",
    )
