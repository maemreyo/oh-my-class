from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Required artifacts per export format
FORMAT_REQUIREMENTS: dict[str, list[str]] = {
    "html": ["lesson"],
    "gift": ["quiz"],
    "h5p": ["quiz", "drill"],
    "qti": ["quiz"],
}

INVERSE_THINKING_FORMAT_SUPPORT: dict[str, str] = {
    "html": "supported",
    "gift": "supported",
    "h5p": "unsupported",
    "qti": "supported",
    "google_forms": "lossy",
}


@dataclass
class ExportValidationResult:
    """Result of export readiness validation."""

    passed: bool
    judge_results: list[dict[str, Any]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    format_issues: dict[str, list[str]] = field(default_factory=dict)


class ExportValidator:
    """Final validation before export packaging.

    Runs 3 independent judge calls with different models.
    2/3 must pass for export to proceed.
    If ≥20% of items fail, stops and asks teacher.
    """

    def __init__(
        self,
        *,
        required_pass_rate: float = 0.67,
        skip_threshold: float = 0.20,
    ) -> None:
        self.required_pass_rate = required_pass_rate
        self.skip_threshold = skip_threshold

    async def validate(
        self,
        artifacts: list[dict[str, Any]],
        export_formats: list[str],
    ) -> ExportValidationResult:
        """Validate export readiness.

        Args:
            artifacts: Generated artifacts to validate.
            export_formats: Requested export formats.

        Returns:
            ExportValidationResult with pass/fail and issues.
        """
        # TODO: Implement export validation
        # 1. Run 3 independent judge calls (different models)
        # 2. Check 2/3 majority pass
        # 3. Validate format-specific artifact requirements
        # 4. Check skip threshold (≥20% fail → stop)
        # 5. Return result
        issues: list[str] = []
        format_issues: dict[str, list[str]] = {}

        # Check format requirements
        artifact_types = {a.get("artifact_type") for a in artifacts}
        for fmt in export_formats:
            required = FORMAT_REQUIREMENTS.get(fmt, [])
            missing = [r for r in required if r not in artifact_types]
            if missing:
                format_issues[fmt] = [
                    f"Missing required artifact type '{r}' for format '{fmt}'"
                    for r in missing
                ]
            if _contains_inverse_thinking(artifacts):
                support = INVERSE_THINKING_FORMAT_SUPPORT.get(fmt, "unsupported")
                if support != "supported":
                    format_issues.setdefault(fmt, []).append(
                        f"Inverse-thinking export format '{fmt}' is {support}; required disaster, clue, safe-zone, and teacher-rationale semantics cannot be preserved."
                    )

        return ExportValidationResult(
            passed=len(issues) == 0 and len(format_issues) == 0,
            issues=issues,
            format_issues=format_issues,
        )


def _contains_inverse_thinking(artifacts: list[dict[str, Any]]) -> bool:
    for artifact in artifacts:
        metadata = artifact.get("metadata")
        methodology = artifact.get("methodology")
        if methodology == "inverse_thinking":
            return True
        if isinstance(metadata, dict) and metadata.get("methodology") == "inverse_thinking":
            return True
    return False
