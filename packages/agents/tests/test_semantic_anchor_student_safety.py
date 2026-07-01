from __future__ import annotations

from common.contracts.vocabulary_batch import AnchorCard, SemanticAnchorCluster


def _semantic_anchor_cluster() -> SemanticAnchorCluster:
    return SemanticAnchorCluster(
        cluster_id="fare-ticket-fee",
        title="Payment and access words",
        title_confidence=0.91,
        raw_input_span="fare / ticket / fee",
        terms=("fare", "ticket", "fee"),
        anchors=(AnchorCard(
            word="fare",
            impression_vi="tiền đi xe",
            core_trigger_en="transport price",
            visual_cue_vi="tay đưa tiền cho tài xế xe buýt",
            semantic_chain=("fare", "transport", "pay", "ride"),
            example_en="The bus fare is two dollars.",
            contrast_note_vi="Fare là số tiền đi lại, không phải tờ vé.",
            student_explanation_vi="Fare là tiền phải trả để đi xe, tàu hoặc máy bay.",
            teacher_script_vi="Teacher-only board script with source nuance.",
            edge_cases=("airfare",),
            source_notes=("Cambridge: fare is money paid for a journey.",),
        ),),
        contrast_notes=("Fare is the transport price; ticket is the proof.",),
        summary_rows=("fare = transport price",),
        review_status="passed",
        warnings=(),
        teacher_source_notes=("Dictionary sources support transport-price nuance.",),
    )


def test_student_projection_excludes_teacher_script_and_source_notes() -> None:
    from packages.agents.sub_agents.content_creator.semantic_anchor_synthesis import semantic_anchor_student_projection

    projection = semantic_anchor_student_projection(_semantic_anchor_cluster())

    anchor = projection.anchors[0]

    assert anchor.word == "fare"
    assert anchor.student_explanation_vi.startswith("Fare là tiền")
    assert not hasattr(anchor, "teacher_script_vi")
    assert not hasattr(anchor, "source_notes")
    assert not hasattr(projection, "teacher_source_notes")
