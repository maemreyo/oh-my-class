"""Tests for I2 hybrid FACT detection — no LLM needed for extractor/classifier."""
from __future__ import annotations
import json
import pytest
from unittest.mock import MagicMock


class TestExtractor:
    def test_extracts_year(self):
        from packages.agents.gates.fact_check.extractor import extract_claims
        claims = extract_claims("The French Revolution began in 1789.")
        assert any(c.claim_type == "date" and "1789" in c.text for c in claims)

    def test_extracts_percentage(self):
        from packages.agents.gates.fact_check.extractor import extract_claims
        claims = extract_claims("About 75% of the Earth is covered by water.")
        assert any(c.claim_type == "statistic" and "75%" in c.text for c in claims)

    def test_extracts_named_entity(self):
        from packages.agents.gates.fact_check.extractor import extract_claims
        claims = extract_claims("Isaac Newton discovered gravity.")
        assert any(c.claim_type == "named_entity" and "Isaac Newton" in c.text for c in claims)

    def test_includes_context_sentence(self):
        from packages.agents.gates.fact_check.extractor import extract_claims
        sentence = "The French Revolution began in 1789."
        claims = extract_claims(sentence)
        date_claims = [c for c in claims if c.claim_type == "date"]
        assert any(sentence.strip() == c.context for c in date_claims)

    def test_empty_text_returns_empty(self):
        from packages.agents.gates.fact_check.extractor import extract_claims
        assert extract_claims("") == []

    def test_pure_text_no_claims(self):
        from packages.agents.gates.fact_check.extractor import extract_claims
        claims = extract_claims("Plants are green.")
        # No dates, stats, formulas; maybe named entities, but no numbers
        assert isinstance(claims, list)

    def test_claim_has_required_fields(self):
        from packages.agents.gates.fact_check.extractor import extract_claims, Claim
        claims = extract_claims("Water is H2O.")
        for c in claims:
            assert isinstance(c, Claim)
            assert hasattr(c, "text")
            assert hasattr(c, "claim_type")
            assert hasattr(c, "context")


class TestRiskClassifier:
    def test_date_is_high_risk(self):
        from packages.agents.gates.fact_check.extractor import Claim
        from packages.agents.gates.fact_check.risk_classifier import classify_risk
        claim = Claim(text="1789", claim_type="date", context="Revolution in 1789")
        assert classify_risk(claim) == "HIGH"

    def test_statistic_is_high_risk(self):
        from packages.agents.gates.fact_check.extractor import Claim
        from packages.agents.gates.fact_check.risk_classifier import classify_risk
        claim = Claim(text="75%", claim_type="statistic", context="75% of Earth")
        assert classify_risk(claim) == "HIGH"

    def test_formula_is_high_risk(self):
        from packages.agents.gates.fact_check.extractor import Claim
        from packages.agents.gates.fact_check.risk_classifier import classify_risk
        claim = Claim(text="H2O", claim_type="formula", context="Water is H2O")
        assert classify_risk(claim) == "HIGH"

    def test_named_entity_near_keyword_is_high_risk(self):
        from packages.agents.gates.fact_check.extractor import Claim
        from packages.agents.gates.fact_check.risk_classifier import classify_risk
        claim = Claim(text="Alexander Graham Bell", claim_type="named_entity",
                      context="Alexander Graham Bell invented the telephone")
        assert classify_risk(claim) == "HIGH"

    def test_named_entity_without_keyword_is_medium(self):
        from packages.agents.gates.fact_check.extractor import Claim
        from packages.agents.gates.fact_check.risk_classifier import classify_risk
        claim = Claim(text="Marie Curie", claim_type="named_entity",
                      context="Marie Curie was a scientist")
        assert classify_risk(claim) == "MEDIUM"

    def test_number_is_low_risk(self):
        from packages.agents.gates.fact_check.extractor import Claim
        from packages.agents.gates.fact_check.risk_classifier import classify_risk
        claim = Claim(text="42", claim_type="number", context="There are 42 students")
        assert classify_risk(claim) == "LOW"

    def test_filter_high_risk(self):
        from packages.agents.gates.fact_check.extractor import Claim
        from packages.agents.gates.fact_check.risk_classifier import filter_high_risk
        claims = [
            Claim(text="1789", claim_type="date", context="In 1789"),
            Claim(text="42", claim_type="number", context="42 students"),
        ]
        high = filter_high_risk(claims)
        assert len(high) == 1
        assert high[0].text == "1789"


class TestFactChecker:
    def test_clean_text_passes_no_llm(self):
        from packages.agents.gates.fact_check.fact_checker import fact_check
        result = fact_check("Plants are green and use sunlight.")
        assert result.passed is True
        assert result.llm_called is False

    def test_no_high_risk_skips_llm(self):
        from packages.agents.gates.fact_check.fact_checker import fact_check
        result = fact_check("Plants use sunlight to make food.", "Grade 3")
        assert result.llm_called is False
        assert result.passed is True

    def test_high_risk_triggers_llm_when_provided(self):
        from packages.agents.gates.fact_check.fact_checker import fact_check
        mock_llm = MagicMock()
        mock_llm.chat.return_value.content = json.dumps([
            {"claim": "1789", "status": "VERIFIED", "note": "Correct"}
        ])
        result = fact_check("The French Revolution began in 1789.", "Grade 8", llm_client=mock_llm)
        assert result.llm_called is True
        mock_llm.chat.assert_called_once()

    def test_high_risk_no_llm_still_passes(self):
        from packages.agents.gates.fact_check.fact_checker import fact_check
        result = fact_check("The French Revolution began in 1789.", "Grade 8")
        assert result.passed is True  # no LLM provided → fast path passes
        assert result.llm_called is False

    def test_skip_llm_flag(self):
        from packages.agents.gates.fact_check.fact_checker import fact_check
        mock_llm = MagicMock()
        result = fact_check("Revolution in 1789.", "Grade 8", llm_client=mock_llm, skip_llm=True)
        assert result.llm_called is False
        mock_llm.chat.assert_not_called()

    def test_incorrect_claim_fails(self):
        from packages.agents.gates.fact_check.fact_checker import fact_check
        mock_llm = MagicMock()
        mock_llm.chat.return_value.content = json.dumps([
            {"claim": "1789", "status": "INCORRECT", "note": "Revolution started in 1787"}
        ])
        result = fact_check("Revolution in 1789.", "Grade 8", llm_client=mock_llm)
        assert result.passed is False
        assert len(result.issues) == 1

    def test_uncertain_claim_still_passes(self):
        from packages.agents.gates.fact_check.fact_checker import fact_check
        mock_llm = MagicMock()
        mock_llm.chat.return_value.content = json.dumps([
            {"claim": "1789", "status": "UNCERTAIN", "note": "Needs verification"}
        ])
        result = fact_check("Revolution in 1789.", "Grade 8", llm_client=mock_llm)
        assert result.passed is True  # uncertain = warning, not failure
        assert "1789" in result.uncertain_claims

    def test_result_has_total_claims_count(self):
        from packages.agents.gates.fact_check.fact_checker import fact_check
        result = fact_check("In 1789, about 75% of France was rural.")
        assert result.total_claims >= 2

    def test_run_fact_check_compat_wrapper(self):
        from packages.agents.gates.fact_check.fact_checker import run_fact_check
        result = run_fact_check("Plants use sunlight.")
        assert "passed" in result
        assert "errors" in result
        assert result["passed"] is True
