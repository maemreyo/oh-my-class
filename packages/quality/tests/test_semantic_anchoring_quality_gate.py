from __future__ import annotations

from common.contracts.vocabulary_batch import AnchorCard, PracticeItem, PracticeSet, SemanticAnchorCluster


def _cluster(review_status: str = "passed") -> SemanticAnchorCluster:
    return SemanticAnchorCluster(
        cluster_id="fare-ticket-fee",
        title="Payment and access words",
        title_confidence=0.9,
        raw_input_span="fare / ticket / fee",
        terms=("fare", "ticket", "fee"),
        anchors=(AnchorCard(
            word="fare",
            impression_vi="tiền đi xe",
            core_trigger_en="transport price",
            visual_cue_vi="trả tiền trên xe buýt",
            semantic_chain=("fare", "transport", "pay"),
            example_en="The bus fare is two dollars.",
            contrast_note_vi="Fare là tiền đi lại, không phải tờ vé.",
            student_explanation_vi="Fare là tiền phải trả để đi xe.",
            teacher_script_vi="Neo fare vào cảnh trả tiền trước khi lên xe buýt.",
            edge_cases=("airfare",),
            source_notes=("Cambridge: fare is money paid for travel.",),
        ),),
        contrast_notes=("Fare is transport price; ticket is proof.",),
        summary_rows=("fare = transport price",),
        review_status=review_status,
        warnings=(),
        teacher_source_notes=("Dictionary sources support the distinction.",),
    )


def _practice() -> PracticeSet:
    return PracticeSet(
        practice_set_id="practice-fare-ticket-fee",
        cluster_id="fare-ticket-fee",
        items=(
            PracticeItem(item_id="item-1", intent="core_trigger_recall", prompt="transport price → ?", answer="fare", rationale="Fare is transport price."),
            PracticeItem(item_id="item-2", intent="context_discrimination", prompt="I bought a ___ to enter.", answer="ticket", rationale="Ticket is access proof."),
        ),
    )


def test_passed_cluster_returns_passed_with_evidence() -> None:
    from packages.quality.semantic_anchoring.gate import SemanticAnchoringQualityGate, SemanticAnchoringQualityInput

    result = SemanticAnchoringQualityGate().evaluate(SemanticAnchoringQualityInput(cluster=_cluster(), practice=_practice()))

    assert result.verdict == "passed"
    assert result.evidence_entry.event_type == "quality_result"
    assert result.evidence_entry.payload["verdict"] == "passed"
    assert result.issues == ()


def test_lexical_uncertainty_returns_needs_review() -> None:
    from packages.quality.semantic_anchoring.gate import SemanticAnchoringQualityGate, SemanticAnchoringQualityInput

    cluster = _cluster(review_status="needs_review")
    cluster = cluster.model_copy(update={"warnings": ("source nuance needs teacher check",)})

    result = SemanticAnchoringQualityGate().evaluate(SemanticAnchoringQualityInput(cluster=cluster, practice=_practice()))

    assert result.verdict == "needs_review"
    assert result.issues[0].failure_class.value == "factual_uncertainty"
    assert result.issues[0].recommended_action == "teacher_review"
