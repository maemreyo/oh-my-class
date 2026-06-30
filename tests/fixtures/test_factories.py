from __future__ import annotations

from common.contracts.artifact import ArtifactContent, TeachingPack
from common.contracts.inverse_thinking import InverseThinkingPack
from packages.quality.layer3_html.html_validator import HTMLValidator

from tests.fixtures.factories import (
    artifact_content_payload,
    inverse_thinking_pack_payload,
    standalone_html_fixture,
    teaching_pack_payload,
)


def test_artifact_factory_returns_valid_contract_payload() -> None:
    artifact = ArtifactContent.model_validate(artifact_content_payload())

    assert artifact.artifact_type == "lesson"


def test_teaching_pack_factory_returns_valid_contract_payload() -> None:
    pack = TeachingPack.model_validate(teaching_pack_payload())

    assert pack.run_id == "run-fixture-inverse-thinking"


def test_inverse_thinking_factory_returns_valid_pack_payload() -> None:
    pack = InverseThinkingPack.model_validate(inverse_thinking_pack_payload())

    assert pack.methodology == "inverse_thinking"


def test_html_factory_returns_quality_gate_safe_document() -> None:
    result = HTMLValidator().validate(standalone_html_fixture())

    assert result.passed is True
