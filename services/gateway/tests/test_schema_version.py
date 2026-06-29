from __future__ import annotations

import pytest

from services.gateway.schema_version import SCHEMA_VERSION, migrate_contract, validate_schema_version
from services.gateway.teaching_pack_types import JsonObject


class TestSchemaVersionValidation:
    def test_current_and_previous_versions_are_supported(self) -> None:
        assert validate_schema_version(SCHEMA_VERSION) is True
        assert validate_schema_version("0.9") is True

    def test_future_and_malformed_versions_are_rejected(self) -> None:
        assert validate_schema_version("9.0") is False
        assert validate_schema_version("1") is False
        assert validate_schema_version("1.0.0") is False
        assert validate_schema_version("v1.0") is False


class TestContractMigration:
    def test_previous_version_adapter_maps_draft_fields_without_mutating_input(self) -> None:
        data: JsonObject = {
            "schema_version": "0.9",
            "artifacts": ["lesson", "quiz"],
            "language": "vi",
            "topic": "Fractions",
        }

        result = migrate_contract(data, "0.9", "1.0")

        assert result == {
            "schema_version": "1.0",
            "artifacts": ["lesson", "quiz"],
            "artifact_types": ["lesson", "quiz"],
            "language": "vi",
            "instruction_language": "vi",
            "topic": "Fractions",
        }
        assert data == {
            "schema_version": "0.9",
            "artifacts": ["lesson", "quiz"],
            "language": "vi",
            "topic": "Fractions",
        }

    def test_previous_version_adapter_preserves_explicit_current_fields(self) -> None:
        data: JsonObject = {
            "schema_version": "0.9",
            "artifacts": ["lesson"],
            "artifact_types": ["worksheet"],
            "language": "vi",
            "instruction_language": "en",
        }

        result = migrate_contract(data, "0.9", "1.0")

        assert result["artifact_types"] == ["worksheet"]
        assert result["instruction_language"] == "en"
        assert result["schema_version"] == "1.0"

    def test_unknown_source_and_target_versions_fail_closed(self) -> None:
        with pytest.raises(ValueError, match="Unsupported source version"):
            migrate_contract({}, "8.0", "1.0")
        with pytest.raises(ValueError, match="Unsupported target version"):
            migrate_contract({}, "1.0", "8.0")
