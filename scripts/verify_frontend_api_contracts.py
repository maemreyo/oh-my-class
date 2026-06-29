from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.gateway.models import RunStatus
from services.gateway.routers.teaching_pack_schemas import (
    TeachingPackCancelResponse,
    TeachingPackCreateRunRequest,
    TeachingPackDeleteResponse,
    TeachingPackRestoreResponse,
    TeachingPackResumeAcceptedResponse,
    TeachingPackResumeRequest,
    TeachingPackRunAcceptedResponse,
    TeachingPackRunStatusResponse,
)
from services.gateway.teaching_pack_gate_registry import (
    TeachingPackGateAction,
    TeachingPackGateName,
)

WEB_CONTRACT_FILE = PROJECT_ROOT / "apps/web/src/types/teaching-pack-api.ts"


def main() -> int:
    source = WEB_CONTRACT_FILE.read_text(encoding="utf-8")
    mismatches = list(_contract_mismatches(source))
    if not mismatches:
        print("✅ Teaching Pack frontend API contracts match backend schemas.")
        return 0
    for mismatch in mismatches:
        print(f"❌ {mismatch}")
    return 1


def _contract_mismatches(source: str) -> list[str]:
    mismatches: list[str] = []
    _compare_set(
        mismatches,
        "TeachingPackRunStatus",
        _extract_union(source, "TeachingPackRunStatus"),
        {status.value for status in RunStatus},
    )
    _compare_set(
        mismatches,
        "TeachingPackGateName",
        _extract_union(source, "TeachingPackGateName"),
        {gate.value for gate in TeachingPackGateName},
    )
    _compare_set(
        mismatches,
        "TeachingPackGateAction",
        _extract_union(source, "TeachingPackGateAction"),
        {action.value for action in TeachingPackGateAction},
    )
    model_checks = {
        "TeachingPackCreateRunRequest": set(TeachingPackCreateRunRequest.model_fields),
        "TeachingPackRunAcceptedResponse": set(TeachingPackRunAcceptedResponse.model_fields),
        "TeachingPackRunStatusResponse": set(TeachingPackRunStatusResponse.model_fields),
        "TeachingPackResumeRequest": set(TeachingPackResumeRequest.model_fields),
        "TeachingPackResumeAcceptedResponse": set(TeachingPackResumeAcceptedResponse.model_fields),
        "TeachingPackCancelResponse": set(TeachingPackCancelResponse.model_fields),
        "TeachingPackDeleteResponse": set(TeachingPackDeleteResponse.model_fields),
        "TeachingPackRestoreResponse": set(TeachingPackRestoreResponse.model_fields),
    }
    for interface_name, expected_fields in model_checks.items():
        _compare_set(
            mismatches,
            interface_name,
            _extract_interface_fields(source, interface_name),
            expected_fields,
        )
    return mismatches


def _compare_set(
    mismatches: list[str],
    label: str,
    actual: set[str],
    expected: set[str],
) -> None:
    missing = expected - actual
    extra = actual - expected
    if missing:
        mismatches.append(f"{label}: missing {sorted(missing)}")
    if extra:
        mismatches.append(f"{label}: extra {sorted(extra)}")


def _extract_union(source: str, type_name: str) -> set[str]:
    pattern = re.compile(rf"export type {type_name}\s*=\s*(?P<body>.*?);", re.DOTALL)
    match = pattern.search(source)
    if match is None:
        return set()
    return set(re.findall(r'"([^"]+)"', match.group("body")))


def _extract_interface_fields(source: str, interface_name: str) -> set[str]:
    pattern = re.compile(rf"export interface {interface_name}\s*{{(?P<body>.*?)}}", re.DOTALL)
    match = pattern.search(source)
    if match is None:
        return set()
    fields: set[str] = set()
    for field_match in re.finditer(r"readonly\s+(\w+)\??\s*:", match.group("body")):
        fields.add(field_match.group(1))
    return fields


if __name__ == "__main__":
    sys.exit(main())
