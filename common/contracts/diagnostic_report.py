"""DiagnosticReport Pydantic models — output contract for the Diagnostic Agent.

Defines the schema for per-student diagnostic analysis: knowledge gaps by section,
Bloom's taxonomy gaps, misconception patterns, and an overall summary.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

BloomLevel = Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
Severity = Literal["critical", "moderate", "minor"]
RecommendedLevel = Literal["B1", "B2", "C1"]
GroupColor = Literal["a", "b", "c", "d", "e"]
ErrorRate = Annotated[float, Field(ge=0.0, le=1.0)]


class KnowledgeGap(BaseModel):
    """A gap identified in a specific knowledge category or section."""

    category: str
    error_count: int
    error_rate: ErrorRate
    severity: Severity
    question_ids: list[int | str]
    confidence: ErrorRate = 0.5


class BloomGap(BaseModel):
    """A gap at a specific Bloom's taxonomy cognitive level."""

    bloom_level: BloomLevel
    vn_name: str
    error_count: int
    error_rate: ErrorRate
    confidence: ErrorRate = 0.5


class MisconceptionPattern(BaseModel):
    """A recurring misconception pattern detected across answers."""

    id: str
    group: GroupColor
    title: str
    description: str
    question_ids: list[int | str]
    systematicity: Literal["systematic", "contextual"] = "contextual"
    confidence: ErrorRate = 0.5


class DiagnosticReport(BaseModel):
    """Complete diagnostic report produced for a single student."""

    student_id: str
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list)
    bloom_gaps: list[BloomGap] = Field(default_factory=list)
    misconception_patterns: list[MisconceptionPattern] = Field(default_factory=list)
    critical_sections: list[str] = Field(default_factory=list)
    overall_error_rate: ErrorRate = 0.0
    recommended_level: RecommendedLevel = "B2"
    summary: str = ""
