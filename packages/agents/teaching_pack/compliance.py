from __future__ import annotations

from dataclasses import dataclass, field

from packages.agents.events import ObservabilityEvent, publish_event
from packages.quality.compliance_policy import ComplianceResultDict, check_artifact_answer_key_leakage, hard_block_violations, html_hard_blocks
from packages.quality.layer2_content.pii import detect_pii

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class ComplianceViolation:
    code: str
    teacher_reason: str
    location: str


@dataclass(frozen=True, slots=True)
class ComplianceResult:
    violations: tuple[ComplianceViolation, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return not self.violations

    def as_dict(self) -> ComplianceResultDict:
        return {
            "passed": self.passed,
            "violations": [violation.code for violation in self.violations],
            "teacher_reasons": [violation.teacher_reason for violation in self.violations],
        }


def compliance_gate_state(state: JsonObject) -> JsonObject:
    result = evaluate_compliance(state)
    if result.passed:
        return {
            "run_id": str(state["run_id"]),
            "compliance_passed": True,
            "compliance_result": result.as_dict(),
        }
    _publish_violations(str(state["run_id"]), result)
    return {
        "run_id": str(state["run_id"]),
        "compliance_passed": False,
        "compliance_result": result.as_dict(),
        "quality_recovery_route": "artifact_workflow",
        "quality_issues": [
            f"compliance.{violation.location}: {violation.code}: {violation.teacher_reason}"
            for violation in result.violations
        ],
        "fail_layer": "compliance",
        "fail_type": "hard_block",
        "fail_context": result.as_dict(),
    }


def evaluate_compliance(state: JsonObject) -> ComplianceResult:
    violations: list[ComplianceViolation] = []
    artifacts = _json_objects(state.get("artifacts"))
    snapshots = _json_objects(state.get("rendered_snapshots"))
    for index, artifact in enumerate(artifacts):
        violations.extend(_artifact_violations(index, artifact))
    for index, snapshot in enumerate(snapshots):
        violations.extend(_snapshot_violations(index, snapshot))
    return ComplianceResult(violations=tuple(violations))


def _artifact_violations(index: int, artifact: JsonObject) -> list[ComplianceViolation]:
    violations: list[ComplianceViolation] = []
    answer_result = check_artifact_answer_key_leakage(artifact)
    violations.extend(
        ComplianceViolation("answer_key_leakage", reason, f"artifacts[{index}]")
        for reason in answer_result["teacher_reasons"]
    )
    pii = detect_pii(artifact)
    for category, count in pii.redaction_counts.items():
        if count > 0:
            violations.append(ComplianceViolation("pii_leakage", f"Student/private {category} data was detected and must be removed.", f"artifacts[{index}]"))
    return violations


def _snapshot_violations(index: int, snapshot: JsonObject) -> list[ComplianceViolation]:
    violations: list[ComplianceViolation] = []
    for field_name in ("student_rendered_html", "rendered_html"):
        html = snapshot.get(field_name)
        if not isinstance(html, str):
            continue
        hard_blocks, _warnings = html_hard_blocks(html, check_answer_key=field_name == "student_rendered_html")
        violations.extend(
            ComplianceViolation(code, _teacher_reason(code), f"rendered_snapshots[{index}].{field_name}")
            for code in hard_blocks
        )
    return violations


def _publish_violations(run_id: str, result: ComplianceResult) -> None:
    for violation in result.violations:
        publish_event(ObservabilityEvent(
            run_id=run_id,
            event_type="hard_block_violation",
            stage="compliance_gate",
            payload={
                "code": violation.code,
                "reason": violation.teacher_reason,
                "location": violation.location,
            },
        ))


def _teacher_reason(code: str) -> str:
    return {
        "schema_invalid": "The content shape is invalid and cannot be safely exported.",
        "missing_doctype": "The HTML document is missing its doctype.",
        "external_assets": "The artifact references external assets and may not work offline.",
        "external_asset": "The artifact references an external asset and may not work offline.",
        "native_radio_inputs": "The artifact uses native radio inputs instead of managed exercise components.",
        "unmanaged_js_runtime": "The artifact loads unmanaged external JavaScript.",
        "missing_brand_string": "The artifact is missing the oh-my-class brand marker.",
        "contrast_below_aa": "Some text does not meet AA contrast requirements.",
        "missing_alt_text": "An image is missing alternative text.",
        "broken_heading_order": "Heading levels skip in a way that harms accessibility.",
        "missing_form_label": "A form control is missing an accessible label.",
        "missing_lang": "The HTML document is missing a language attribute.",
        "missing_long_description": "A meaningful SVG is missing a long description.",
        "answer_key_leakage": "Answer key material appears in student-facing content.",
        "pii_leakage": "Student or private personal data appears in generated content.",
        "teacher_gate_not_approved": "Teacher approval has not been recorded.",
    }.get(code, "A deterministic compliance policy blocked this artifact.")


def _json_objects(value: JsonValue | None) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


__all__ = ["ComplianceResult", "ComplianceViolation", "compliance_gate_state", "evaluate_compliance", "hard_block_violations"]
