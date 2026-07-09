"""PublishTarget enum: Google Forms moved from ExportFormat to PublishTarget.

TDD — these tests define the expected contract before implementation.
"""
from __future__ import annotations

from typing import get_args

import pytest
from pydantic import ValidationError

from common.contracts.run_contract import (
    ContractRevisionMeta,
    ExportFormat,
    PublishTarget,
    RunContract,
)


def _revision() -> ContractRevisionMeta:
    return ContractRevisionMeta(
        revision=1,
        actor="system",
        source="code_defaults",
        reason="test publish target",
        effective_stage="setup_contract",
    )


def _contract(**overrides: object) -> RunContract:
    base = {
        "contract_id": "c-1",
        "run_id": "r-1",
        "teacher_id": "t-1",
        "topic": "Fractions",
        "grade_band": "Grade 5",
        "subject": "math",
        "locale": "vi-VN",
        "instruction_language": "vi",
        "citation_locale": "vi-VN",
        "artifact_types": ["lesson"],
        "export_formats": ["html"],
        "config_version": "v1",
        "config_hash": "a" * 64,
        "revision_meta": _revision(),
    }
    base.update(overrides)
    return RunContract(**base)


# ── PublishTarget enum ──────────────────────────────────────────────────────


class TestPublishTargetEnum:
    def test_publish_target_has_google_forms_value(self) -> None:
        values = set(get_args(PublishTarget))
        assert "google_forms" in values

    def test_publish_target_is_extensible_literal(self) -> None:
        """PublishTarget should be a Literal type, not a closed enum."""
        assert isinstance(get_args(PublishTarget), tuple)


# ── ExportFormat no longer includes google_forms ─────────────────────────────


class TestExportFormatExcludesGoogleForms:
    def test_google_forms_removed_from_export_format(self) -> None:
        values = set(get_args(ExportFormat))
        assert "google_forms" not in values

    def test_export_format_still_has_html(self) -> None:
        values = set(get_args(ExportFormat))
        assert "html" in values

    def test_export_format_still_has_gift(self) -> None:
        values = set(get_args(ExportFormat))
        assert "gift" in values


# ── RunContract.publish_targets field ────────────────────────────────────────


class TestRunContractPublishTargets:
    def test_publish_targets_defaults_to_empty_list(self) -> None:
        contract = _contract()
        assert contract.publish_targets == []

    def test_publish_targets_accepts_google_forms(self) -> None:
        contract = _contract(publish_targets=["google_forms"])
        assert contract.publish_targets == ["google_forms"]

    def test_publish_targets_rejects_invalid_value(self) -> None:
        with pytest.raises(ValidationError):
            _contract(publish_targets=["invalid_target"])

    def test_backward_compatible_without_publish_targets(self) -> None:
        """Contracts without publish_targets still parse (Field default_factory)."""
        contract = _contract()
        assert contract.publish_targets == []

    def test_contract_with_both_export_and_publish(self) -> None:
        contract = _contract(
            export_formats=["html", "gift"],
            publish_targets=["google_forms"],
        )
        assert contract.export_formats == ["html", "gift"]
        assert contract.publish_targets == ["google_forms"]
