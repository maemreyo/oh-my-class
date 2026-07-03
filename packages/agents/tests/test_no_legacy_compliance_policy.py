from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LEGACY_POLICY_FILES = (
    PROJECT_ROOT / "packages" / "agents" / "middleware" / "safety" / "guardrail.py",
    PROJECT_ROOT / "packages" / "agents" / "gates" / "presentation" / "html_validator.py",
    PROJECT_ROOT / "packages" / "agents" / "gates" / "presentation" / "answer_key_guard.py",
    PROJECT_ROOT / "packages" / "agents" / "config" / "gate_config.py",
    PROJECT_ROOT / "packages" / "quality" / "layer3_html" / "html_validator.py",
    PROJECT_ROOT / "packages" / "quality" / "layer4_judge" / "hard_blocks.py",
)
FORBIDDEN_POLICY_OWNERS = (
    "EMAIL_PATTERN",
    "PHONE_PATTERN",
    "DOCTYPE_PATTERN",
    "EXTERNAL_ASSET_PATTERNS",
    "EXTERNAL_ASSET_PATTERN",
    "HARD_BLOCKS",
    "ANSWER_LEAK_PATTERNS",
    "STUDENT_ARTIFACT_TYPES",
    "block_missing_doctype",
    "block_external_assets",
    "block_answer_key_leakage",
    "block_missing_brand",
)


def test_legacy_surfaces_do_not_own_compliance_policy() -> None:
    offenders: list[str] = []
    for path in LEGACY_POLICY_FILES:
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_POLICY_OWNERS:
            if re.search(rf"\b{re.escape(forbidden)}\b", text):
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {forbidden}")

    assert offenders == []


def test_compliance_policy_is_single_hard_block_owner() -> None:
    from packages.quality.compliance_policy import COMPLIANCE_HARD_BLOCK_CODES

    assert {
        "missing_doctype",
        "external_assets",
        "answer_key_leakage",
        "pii_leakage",
        "native_radio_inputs",
        "unmanaged_js_runtime",
        "missing_brand_string",
    } <= COMPLIANCE_HARD_BLOCK_CODES
