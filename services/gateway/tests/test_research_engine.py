from __future__ import annotations

from common.contracts.run_contract import ContractRevisionMeta, JsonObject, RunContract
from services.gateway.research_engine import (
    FetchResult,
    RankedSearchCandidate,
    SearchCandidate,
    build_research_brief,
    extract_evidence,
    normalize_search_candidates,
    plan_search,
    rank_search_candidates,
)


class TestResearchEngine:
    def test_math_misconception_plan_has_targeted_scrubbed_queries(self) -> None:
        contract = _contract(
            topic="Fractions",
            subject="math",
            evidence={
                "student_name": "An",
                "email": "an@example.com",
                "misconceptions": ["equivalent fractions"],
            },
        )

        plan = plan_search(contract)

        assert len(plan.queries) >= 2
        rendered = " ".join(query.query for query in plan.queries)
        assert "equivalent fractions" in rendered
        assert "An" not in rendered
        assert "an@example.com" not in rendered

    def test_search_queries_scrub_student_names_from_topic(self) -> None:
        contract = _contract(
            topic="Teach fractions to student Mai Nguyen",
            subject="math",
        )

        plan = plan_search(contract)

        rendered = " ".join(query.query for query in plan.queries)
        assert "Mai" not in rendered
        assert "Nguyen" not in rendered
        assert "student" in rendered

    def test_english_esl_plan_has_language_specific_queries(self) -> None:
        contract = _contract(topic="Past tense", subject="english", language="vi")

        plan = plan_search(contract)

        rendered = " ".join(query.query for query in plan.queries)
        assert "ESL" in rendered
        assert "Past tense" in rendered

    def test_search_plan_confirmation_triggers_for_ambiguous_curriculum(self) -> None:
        contract = _contract(topic="Fractions", subject="math", locale="vi-VN", curriculum=None)

        plan = plan_search(contract)

        assert plan.requires_confirmation is True
        assert plan.confirmation_reasons == ("ambiguous_curriculum",)

    def test_normalization_dedupes_tracking_fragments_and_blocks_domains(self) -> None:
        candidates = normalize_search_candidates((
            SearchCandidate("A", "http://Example.com/a?utm_source=x#top", "one"),
            SearchCandidate("B", "https://example.com/a", "two"),
            SearchCandidate("C", "https://blocked.test/a", "blocked"),
        ), blocked_domains=frozenset({"blocked.test"}))

        assert [(item.title, item.normalized_url) for item in candidates] == [
            ("A", "https://example.com/a"),
        ]

    def test_ranking_prefers_teacher_sources_without_losing_domain_diversity(self) -> None:
        candidates = (
            SearchCandidate("Teacher", "https://teacher.test/a", "teacher source"),
            SearchCandidate("Preferred", "https://edu.test/a", "curriculum source"),
            SearchCandidate("Preferred 2", "https://edu.test/b", "curriculum source"),
            SearchCandidate("Preferred 3", "https://edu.test/c", "curriculum source"),
            SearchCandidate("Other", "https://other.test/a", "other source"),
        )

        ranked = rank_search_candidates(
            normalize_search_candidates(candidates, blocked_domains=frozenset()),
            teacher_sources=frozenset({"https://teacher.test/a"}),
            preferred_domains=frozenset({"edu.test"}),
            max_per_domain=2,
        )

        assert ranked[0].source_id == "source-1"
        assert ranked[0].url == "https://teacher.test/a"
        assert sum(1 for item in ranked if item.domain == "edu.test") == 2

    def test_brief_contains_citations_not_raw_pages(self) -> None:
        ranked = (
            RankedSearchCandidate(
                "source-1",
                "Photosynthesis",
                "https://edu.test/photosynthesis",
                "edu.test",
                0.9,
            ),
            RankedSearchCandidate(
                "source-2",
                "Plant Lab",
                "https://lab.test/plants",
                "lab.test",
                0.7,
            ),
        )
        evidence = extract_evidence(
            (
                FetchResult(
                    "source-1",
                    "Photosynthesis converts light energy into chemical energy. Raw page tail.",
                ),
                FetchResult(
                    "source-2",
                    "A classroom plant lab can compare light and dark conditions.",
                ),
            ),
            ranked,
        )

        brief = build_research_brief(
            topic="Photosynthesis",
            subject="science",
            evidence=evidence,
            ranked_candidates=ranked,
        )

        assert brief.topic == "Photosynthesis"
        assert [citation.source_id for citation in brief.citations] == ["source-1", "source-2"]
        assert all("Raw page tail" not in finding for finding in brief.key_findings)
        assert brief.artifact_guidance[0].citation_ids == ["source-1", "source-2"]


def _contract(
    *,
    topic: str,
    subject: str,
    locale: str = "en-US",
    language: str = "en",
    curriculum: str | None = "Common Core",
    evidence: JsonObject | None = None,
) -> RunContract:
    return RunContract(
        contract_id="contract-test",
        run_id="run-test",
        teacher_id="teacher-test",
        topic=topic,
        grade_band="Grade 5",
        subject=subject,
        locale=locale,
        instruction_language=language,
        curriculum=curriculum,
        citation_locale=locale,
        artifact_types=["lesson", "worksheet"],
        export_formats=["html"],
        research_policy="standard",
        config_version="test",
        config_hash="0" * 64,
        student_evidence=evidence,
        revision_meta=ContractRevisionMeta(
            revision=1,
            actor="system",
            source="request",
            reason="test",
            effective_stage="setup_contract",
        ),
    )
