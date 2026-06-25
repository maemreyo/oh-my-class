"""Research bundle Pydantic models — output contract for the Researcher Agent.

Follows the FACT protocol (Find → Assess → Cross-reference → Tag).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ResearchSource(BaseModel):
    """A single research source with credibility assessment."""

    title: str = Field(..., min_length=1, max_length=500)
    url: str | None = Field(default=None, max_length=2000)
    credibility_score: float = Field(..., ge=0.0, le=1.0)
    verification_status: Literal["VERIFIED", "MODIFIED", "REMOVED", "UNCERTAIN"]


class ResearchBundle(BaseModel):
    """Structured research output from the Researcher Agent.

    Follows the FACT protocol (Find → Assess → Cross-reference → Tag).
    Minimum sources depend on research_policy.
    """

    topic: str = Field(..., min_length=1, max_length=200)
    sources: list[ResearchSource] = Field(
        ...,
        min_length=2,
        description="Minimum 2 sources for basic, 5+ for standard, 10+ for rigorous",
    )
    key_findings: list[str | dict[str, Any]] = Field(default_factory=list)
    cross_references: list[dict[str, Any]] = Field(default_factory=list)
    research_policy: Literal["basic", "standard", "rigorous"] = "standard"
