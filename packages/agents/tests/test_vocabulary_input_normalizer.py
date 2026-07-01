from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.vocabulary_batch import InputNormalizationReport
from packages.agents.teaching_pack.vocabulary_input_normalizer import normalize_vocabulary_input


def test_parses_slash_comma_and_vietnamese_title_hints() -> None:
    report = normalize_vocabulary_input(
        """
        Chủ đề: Travel words
        travel / journey / trip / voyage
        fare, ticket, fee
        historic historical classic classical
        """,
    )

    assert [cluster.terms for cluster in report.ready_clusters] == [
        ("travel", "journey", "trip", "voyage"),
        ("fare", "ticket", "fee"),
        ("historic", "historical", "classic", "classical"),
    ]
    assert report.ready_clusters[0].title_hint == "Travel words"
    assert report.parse_confidence > 0.8


def test_attaches_free_form_notes_to_intended_cluster() -> None:
    report = normalize_vocabulary_input(
        """
        travel / journey / trip
        Note: học sinh hay nhầm journey với trip trong bài viết
        fare / fee / fine
        Ghi chú: cần ví dụ về tiền phạt
        """,
    )

    assert report.ready_clusters[0].notes == ("học sinh hay nhầm journey với trip trong bài viết",)
    assert report.ready_clusters[1].notes == ("cần ví dụ về tiền phạt",)


def test_ambiguous_spans_do_not_block_ready_clusters() -> None:
    report = normalize_vocabulary_input(
        """
        travel / journey / trip
        bank
        light / light
        """,
    )

    assert report.ready_clusters[0].terms == ("travel", "journey", "trip")
    assert [cluster.raw_input_span for cluster in report.ambiguous_clusters] == ["bank", "light / light"]
    assert len(report.clarifying_questions) == 2


def test_overlapping_clusters_are_flagged_not_silently_merged() -> None:
    report = normalize_vocabulary_input(
        """
        travel / journey / trip
        journey / voyage / excursion
        """,
    )

    assert len(report.ready_clusters) == 2
    assert report.ambiguous_clusters[0].terms == ("journey",)
    assert "journey" in report.clarifying_questions[0]


def test_structured_output_validation_fails_closed_on_malformed_output() -> None:
    with pytest.raises(ValidationError):
        InputNormalizationReport(
            report_id="norm-bad",
            ready_clusters=[{"cluster_id": "cluster-1", "terms": ["only-one"], "raw_input_span": "only-one"}],
            ambiguous_clusters=(),
            clarifying_questions=(),
            skipped_spans=(),
            parse_confidence=1.2,
        )
