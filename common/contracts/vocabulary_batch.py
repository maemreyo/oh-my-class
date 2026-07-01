from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ClusterStatus = Literal["passed", "needs_review", "failed"]
SourceVerificationStatus = Literal["VERIFIED", "MODIFIED", "REMOVED", "UNCERTAIN"]
LexicalGroundingReadiness = Literal["passed", "needs_review", "failed"]
LexicalGroundingStudentField = Literal[
    "term_definitions",
    "usage_constraints",
    "common_confusions",
    "example_pairs",
    "distinction_notes",
]
PracticeIntent = Literal[
    "core_trigger_recall",
    "context_discrimination",
    "boundary_explanation",
    "reverse_retrieval",
]
ClusterExportRef = Literal[
    "teacher_teaching_html",
    "student_teaching_html",
    "teacher_practice_html",
    "student_practice_html",
    "teacher_review_html",
    "diagnostic_report",
    "gift",
    "h5p",
]


class ClusterExportPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: tuple[ClusterExportRef, ...] = Field(min_length=1)
    needs_review: tuple[ClusterExportRef, ...] = Field(min_length=1)
    failed: tuple[ClusterExportRef, ...] = Field(min_length=1)

    @field_validator("needs_review")
    @classmethod
    def _needs_review_exports_teacher_only(
        cls,
        value: tuple[ClusterExportRef, ...],
    ) -> tuple[ClusterExportRef, ...]:
        student_exports = {"student_teaching_html", "student_practice_html", "gift", "h5p"}
        if any(export_ref in student_exports for export_ref in value):
            msg = "needs_review clusters may only export teacher review files"
            raise ValueError(msg)
        return value


class VocabularyBatchConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    batch_id: str = Field(min_length=1, max_length=120)
    teacher_id: str = Field(min_length=1, max_length=120)
    locale: str = Field(min_length=2, max_length=16)
    target_cefr: str | None = Field(default=None, max_length=16)
    max_clusters: int = Field(ge=1, le=100)
    default_export_policy: ClusterExportPolicy


class NormalizedVocabularyCluster(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster_id: str = Field(min_length=1, max_length=120)
    terms: tuple[str, ...] = Field(min_length=2)
    raw_input_span: str = Field(min_length=1, max_length=1000)
    title_hint: str | None = Field(default=None, max_length=200)
    notes: tuple[str, ...] = Field(default=())
    confidence: float = Field(ge=0.0, le=1.0)


class AmbiguousVocabularyCluster(BaseModel):
    model_config = ConfigDict(frozen=True)

    span_id: str = Field(min_length=1, max_length=120)
    raw_input_span: str = Field(min_length=1, max_length=1000)
    terms: tuple[str, ...] = Field(default=())
    reason: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)


class InputNormalizationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str = Field(min_length=1, max_length=120)
    ready_clusters: tuple[NormalizedVocabularyCluster, ...] = Field(default=())
    ambiguous_clusters: tuple[AmbiguousVocabularyCluster, ...] = Field(default=())
    clarifying_questions: tuple[str, ...] = Field(default=())
    skipped_spans: tuple[str, ...] = Field(default=())
    parse_confidence: float = Field(ge=0.0, le=1.0)


class LexicalGroundingSourceEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=500)
    url: str | None = Field(default=None, max_length=2000)
    excerpt: str = Field(min_length=1, max_length=2000)
    verification_status: SourceVerificationStatus


class LexicalGroundingRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster: NormalizedVocabularyCluster
    source_evidence: tuple[LexicalGroundingSourceEvidence, ...] = Field(default=())
    cluster_snapshot_hash: str = Field(min_length=1, max_length=120)


class LexicalTermDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    term: str = Field(min_length=1, max_length=120)
    definition: str = Field(min_length=1, max_length=700)
    source_ids: tuple[str, ...] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class LexicalUsageConstraint(BaseModel):
    model_config = ConfigDict(frozen=True)

    term: str = Field(min_length=1, max_length=120)
    constraint: str = Field(min_length=1, max_length=700)
    source_ids: tuple[str, ...] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class LexicalExamplePair(BaseModel):
    model_config = ConfigDict(frozen=True)

    term: str = Field(min_length=1, max_length=120)
    example: str = Field(min_length=1, max_length=700)
    counterexample: str = Field(min_length=1, max_length=700)
    contrast_note: str = Field(min_length=1, max_length=700)
    source_ids: tuple[str, ...] = Field(min_length=1)


class LexicalGroundingCacheKeys(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster_snapshot_key: str = Field(min_length=1, max_length=200)
    term_distinction_key: str = Field(min_length=1, max_length=500)


class LexicalGroundingBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    bundle_id: str = Field(min_length=1, max_length=120)
    cluster_id: str = Field(min_length=1, max_length=120)
    terms: tuple[str, ...] = Field(min_length=2)
    source_ids: tuple[str, ...] = Field(min_length=1)
    term_definitions: tuple[LexicalTermDefinition, ...] = Field(default=())
    usage_constraints: tuple[LexicalUsageConstraint, ...] = Field(default=())
    common_confusions: tuple[str, ...] = Field(default=())
    example_pairs: tuple[LexicalExamplePair, ...] = Field(default=())
    distinction_notes: tuple[str, ...] = Field(min_length=1)
    teacher_source_notes: tuple[str, ...] = Field(default=())
    student_projection_fields: tuple[LexicalGroundingStudentField, ...] = Field(default=())
    confidence: float = Field(ge=0.0, le=1.0)
    readiness: LexicalGroundingReadiness
    cache_keys: LexicalGroundingCacheKeys
    uncertainty_flags: tuple[str, ...] = Field(default=())

    @model_validator(mode="after")
    def _uncertain_when_evidence_is_thin(self) -> LexicalGroundingBundle:
        if len(self.source_ids) < 2 and (self.readiness == "passed" or self.confidence > 0.6):
            msg = "lexical grounding with fewer than 2 sources must stay needs_review with confidence <= 0.6"
            raise ValueError(msg)
        return self


class AnchorCard(BaseModel):
    model_config = ConfigDict(frozen=True)

    word: str = Field(min_length=1, max_length=120)
    impression_vi: str = Field(min_length=1, max_length=300)
    core_trigger_en: str = Field(min_length=1, max_length=120)
    visual_cue_vi: str = Field(min_length=1, max_length=300)
    semantic_chain: tuple[str, ...] = Field(min_length=1, max_length=8)
    example_en: str = Field(min_length=1, max_length=500)
    contrast_note_vi: str = Field(min_length=1, max_length=500)
    student_explanation_vi: str = Field(min_length=1, max_length=700)
    teacher_script_vi: str = Field(min_length=1, max_length=1000)
    edge_cases: tuple[str, ...] = Field(default=())
    source_notes: tuple[str, ...] = Field(default=())


class SemanticAnchorCluster(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    title_confidence: float = Field(ge=0.0, le=1.0)
    raw_input_span: str = Field(min_length=1, max_length=1000)
    terms: tuple[str, ...] = Field(min_length=2)
    anchors: tuple[AnchorCard, ...] = Field(min_length=1)
    contrast_notes: tuple[str, ...] = Field(min_length=1)
    summary_rows: tuple[str, ...] = Field(min_length=1)
    review_status: ClusterStatus
    warnings: tuple[str, ...] = Field(default=())
    teacher_source_notes: tuple[str, ...] = Field(default=())


class PracticeItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str = Field(min_length=1, max_length=120)
    intent: PracticeIntent
    prompt: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=1000)


class PracticeSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    practice_set_id: str = Field(min_length=1, max_length=120)
    cluster_id: str = Field(min_length=1, max_length=120)
    items: tuple[PracticeItem, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _contains_distinct_practice_intents(self) -> PracticeSet:
        if len({item.intent for item in self.items}) != len(self.items):
            msg = "practice items must not duplicate exercise intents within a set"
            raise ValueError(msg)
        return self


class ClusterProjectionRefs(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster_id: str = Field(min_length=1, max_length=120)
    teaching_teacher_html: str = Field(min_length=1, max_length=500)
    teaching_student_html: str = Field(min_length=1, max_length=500)
    practice_teacher_html: str = Field(min_length=1, max_length=500)
    practice_student_html: str = Field(min_length=1, max_length=500)
