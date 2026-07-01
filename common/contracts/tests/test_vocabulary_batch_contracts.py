from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.vocabulary_batch import (
    AnchorCard,
    AmbiguousVocabularyCluster,
    ClusterExportPolicy,
    ClusterProjectionRefs,
    InputNormalizationReport,
    LexicalGroundingCacheKeys,
    LexicalGroundingBundle,
    NormalizedVocabularyCluster,
    PracticeItem,
    PracticeSet,
    SemanticAnchorCluster,
    VocabularyBatchConfig,
)


def _anchor(word: str = "voyage") -> AnchorCard:
    return AnchorCard(
        word=word,
        impression_vi="hoành tráng / dài ngày",
        core_trigger_en="explore",
        visual_cue_vi="tàu thủy lớn hoặc phi thuyền",
        semantic_chain=("voyage", "long journey", "explore"),
        example_en="The voyage across the ocean took months.",
        contrast_note_vi="Voyage nhấn mạnh hành trình dài hoặc trang trọng.",
        student_explanation_vi="Dùng voyage khi chuyến đi dài và có cảm giác khám phá.",
        teacher_script_vi="Nhấn hình ảnh con tàu lớn để học sinh nhớ sắc thái dài ngày.",
        edge_cases=("space voyage",),
        source_notes=("Cambridge: voyage often means long journey by sea or space.",),
    )


def _practice_set() -> PracticeSet:
    return PracticeSet(
        practice_set_id="practice-1",
        cluster_id="cluster-1",
        items=(
            PracticeItem(
                item_id="item-1",
                intent="core_trigger_recall",
                prompt="Which word matches a long sea journey?",
                answer="voyage",
                rationale="Voyage carries the long sea journey anchor.",
            ),
        ),
    )


def test_happy_path_vocabulary_batch_contracts_validate() -> None:
    config = VocabularyBatchConfig(
        batch_id="batch-1",
        teacher_id="teacher-1",
        locale="vi-VN",
        target_cefr="B1",
        max_clusters=50,
        default_export_policy=ClusterExportPolicy(
            passed=("teacher_teaching_html", "student_teaching_html", "gift"),
            needs_review=("teacher_review_html",),
            failed=("diagnostic_report",),
        ),
    )
    normalization = InputNormalizationReport(
        report_id="norm-1",
        ready_clusters=(NormalizedVocabularyCluster(
            cluster_id="cluster-1",
            terms=("travel", "journey", "trip"),
            raw_input_span="travel / journey / trip",
            title_hint="Travel words",
            notes=(),
            confidence=0.95,
        ),),
        ambiguous_clusters=(AmbiguousVocabularyCluster(
            span_id="ambiguous-1",
            raw_input_span="bank",
            terms=("bank",),
            reason="Only one term was found.",
            confidence=0.3,
        ),),
        clarifying_questions=(),
        skipped_spans=(),
        parse_confidence=0.95,
    )
    grounding = LexicalGroundingBundle(
        bundle_id="ground-1",
        cluster_id="cluster-1",
        terms=("travel", "journey", "trip", "voyage"),
        source_ids=("cambridge-voyage", "oxford-voyage"),
        distinction_notes=("Voyage is often longer or more formal than trip.",),
        student_projection_fields=("distinction_notes",),
        confidence=0.86,
        readiness="passed",
        cache_keys=LexicalGroundingCacheKeys(
            cluster_snapshot_key="lexical-grounding:cluster:snapshot-1",
            term_distinction_key="lexical-grounding:terms:journey|travel|trip|voyage",
        ),
        uncertainty_flags=(),
    )
    cluster = SemanticAnchorCluster(
        cluster_id="cluster-1",
        title="Travel words",
        title_confidence=0.9,
        raw_input_span="travel / journey / trip / voyage",
        terms=("travel", "journey", "trip", "voyage"),
        anchors=(_anchor(),),
        contrast_notes=("Trip is shorter and purpose-based; voyage is longer.",),
        summary_rows=("voyage = long/exploratory journey",),
        review_status="needs_review",
        warnings=("Check local exam examples before final export.",),
        teacher_source_notes=("Dictionary examples verified from two sources.",),
    )
    projections = ClusterProjectionRefs(
        cluster_id="cluster-1",
        teaching_teacher_html="clusters/cluster-1/teaching.teacher.html",
        teaching_student_html="clusters/cluster-1/teaching.student.html",
        practice_teacher_html="clusters/cluster-1/practice.teacher.html",
        practice_student_html="clusters/cluster-1/practice.student.html",
    )

    assert config.default_export_policy.passed == ("teacher_teaching_html", "student_teaching_html", "gift")
    assert normalization.ready_clusters[0].terms == ("travel", "journey", "trip")
    assert grounding.source_ids == ("cambridge-voyage", "oxford-voyage")
    assert cluster.anchors[0].word == "voyage"
    assert _practice_set().items[0].intent == "core_trigger_recall"
    assert projections.practice_student_html.endswith("practice.student.html")


def test_rejects_invalid_cluster_status() -> None:
    with pytest.raises(ValidationError):
        SemanticAnchorCluster(
            cluster_id="cluster-1",
            title="Travel words",
            title_confidence=0.9,
            raw_input_span="travel / journey",
            terms=("travel", "journey"),
            anchors=(_anchor(),),
            contrast_notes=("Travel is general; journey emphasizes process.",),
            summary_rows=("journey = process",),
            review_status="approved",
            warnings=(),
            teacher_source_notes=(),
        )


def test_rejects_missing_bilingual_anchor_fields() -> None:
    with pytest.raises(ValidationError):
        AnchorCard(
            word="journey",
            impression_vi="",
            core_trigger_en="path",
            visual_cue_vi="con đường dài",
            semantic_chain=("journey",),
            example_en="Life is a journey.",
            contrast_note_vi="Journey nhấn quá trình.",
            student_explanation_vi="Journey là hành trình có quá trình.",
            teacher_script_vi="Dùng hình ảnh con đường.",
            edge_cases=(),
            source_notes=(),
        )


def test_rejects_malformed_export_policy() -> None:
    with pytest.raises(ValidationError):
        ClusterExportPolicy(passed=(), needs_review=("student_teaching_html",), failed=())


def test_practice_set_is_separate_from_semantic_anchor_cluster() -> None:
    cluster_fields = SemanticAnchorCluster.model_fields

    assert "practice_set" not in cluster_fields
    assert _practice_set().cluster_id == "cluster-1"
