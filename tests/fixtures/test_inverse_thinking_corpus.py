from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from common.contracts.artifact import ArtifactContent
from common.contracts.inverse_thinking import InverseThinkingPack
from packages.methodologies.inverse_thinking import project_drill, project_lesson, project_quiz, project_worksheet
from packages.quality.layer2_content.inverse_thinking import validate_inverse_thinking_pack
from tests.fixtures.inverse_thinking.corpus import (
    CorpusCase,
    fixture_sha256,
    inverse_thinking_fixture_root,
    load_all_fixtures,
    load_negative_fixtures,
    load_positive_fixtures,
)

_PROJECTORS = {
    "lesson": project_lesson,
    "worksheet": project_worksheet,
    "quiz": project_quiz,
    "drill": project_drill,
}

_PII_PATTERNS = (
    re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    re.compile(r"\b(?:\+?\d[\s.-]?){9,}\b"),
    re.compile(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b"),
)


def test_manifest_references_every_fixture_exactly_once() -> None:
    root = inverse_thinking_fixture_root()
    cases = load_all_fixtures()
    manifest_paths = [case.path.relative_to(root) for case in cases]
    actual_paths = sorted(path.relative_to(root) for path in root.glob("*/*.json"))

    assert sorted(manifest_paths) == actual_paths
    assert len(manifest_paths) == len(set(manifest_paths))
    assert len({case.case_id for case in cases}) == len(cases)


def test_manifest_hashes_detect_fixture_drift() -> None:
    mismatches = [
        f"{case.path.relative_to(inverse_thinking_fixture_root())}: old={case.sha256} new={fixture_sha256(case.path)}"
        for case in load_all_fixtures()
        if fixture_sha256(case.path) != case.sha256
    ]

    assert mismatches == []


@pytest.mark.parametrize("case", load_positive_fixtures(), ids=lambda case: case.case_id)
def test_positive_fixtures_validate_against_contract(case: CorpusCase) -> None:
    pack = InverseThinkingPack.model_validate(case.data["pack"])

    assert pack.methodology == "inverse_thinking"


@pytest.mark.parametrize("case", load_negative_fixtures(), ids=lambda case: case.case_id)
def test_negative_fixtures_fail_with_expected_issue(case: CorpusCase) -> None:
    expected = case.data["expected_issue"]
    if "pack" in case.data:
        result = validate_inverse_thinking_pack(case.data["pack"])

        assert not result.passed
        assert any(issue.code == expected["code"] and issue.severity == expected["severity"] for issue in result.issues)
        return

    with pytest.raises(ValidationError, match=r"sections\[0\]\.components\[0\]"):
        ArtifactContent.model_validate(case.data["artifact"])


@pytest.mark.parametrize("case", load_positive_fixtures(), ids=lambda case: case.case_id)
def test_positive_fixtures_project_to_expected_artifacts(case: CorpusCase) -> None:
    expected_outputs = case.data["expected_projection_outputs"]

    for artifact_type in expected_outputs:
        projection = _PROJECTORS[artifact_type](case.data["pack"])
        assert projection.artifact_type == artifact_type
        assert projection.student_components


def test_fixture_corpus_has_no_external_urls_or_pii() -> None:
    for path in inverse_thinking_fixture_root().glob("*/*.json"):
        text = path.read_text(encoding="utf-8")
        assert "http://" not in text
        assert "https://" not in text
        for pattern in _PII_PATTERNS:
            assert pattern.search(text) is None, path


def test_fixture_readme_documents_add_and_manifest_update() -> None:
    readme = (inverse_thinking_fixture_root() / "README.md").read_text(encoding="utf-8")

    assert "Add or update a fixture" in readme
    assert "manifest.json" in readme
    assert "shasum -a 256" in readme


def test_fixture_metadata_is_complete() -> None:
    required = {"case_id", "subject", "grade_band", "locale", "expected_gate_outcome", "expected_projection_outputs"}
    for case in load_all_fixtures():
        assert required <= set(case.data)
        assert case.data["case_id"] == case.case_id


def test_manifest_json_is_stable_sorted() -> None:
    manifest_path = inverse_thinking_fixture_root() / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = [entry["path"] for entry in manifest["fixtures"]]

    assert paths == sorted(paths)
