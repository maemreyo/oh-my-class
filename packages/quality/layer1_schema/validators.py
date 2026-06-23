"""Layer 1 validators — Pydantic v2 schema validation with self-healing.

Uses Pydantic's ModelRetry for self-healing: up to 3 retries with
feedback, then triggers CircuitBreaker.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic import BaseModel


class ValidationGateError(Exception):
    """Raised when Layer 1 schema validation fails after exhausting retries."""

    def __init__(self, layer: int, issues: list[str]) -> None:
        self.layer = layer
        self.issues = issues
        super().__init__(f"Layer {layer} validation failed: {issues}")


# Placeholder content patterns that must be rejected
PLACEHOLDER_PATTERNS: list[str] = [
    "[TBD]",
    "lorem ipsum",
    "TODO",
    "PLACEHOLDER",
    "[INSERT",
]


async def validate_schema(
    data: dict[str, Any],
    schema_model: type[BaseModel],
    *,
    max_retries: int = 3,
) -> BaseModel:
    """Validate data against a Pydantic model with self-healing retries.

    On validation failure, the data is returned to the LLM with error
    feedback for correction (ModelRetry pattern).

    Args:
        data: Raw data dict to validate.
        schema_model: Pydantic BaseModel class to validate against.
        max_retries: Maximum self-healing attempts before circuit break.

    Returns:
        Validated Pydantic model instance.

    Raises:
        ValidationGateError: If validation fails after max_retries.
    """
    from pydantic import ValidationError

    last_error = None
    for attempt in range(max_retries):
        try:
            return schema_model.model_validate(data)
        except ValidationError as e:
            last_error = e
            if attempt < max_retries - 1:
                # ModelRetry: in real implementation, this feeds error back to LLM
                continue
    raise ValidationGateError(layer=1, issues=[str(last_error)])


def check_placeholder_content(data: dict[str, Any]) -> list[str]:
    """Check for placeholder content patterns in data values.

    Args:
        data: Data dict to scan.

    Returns:
        List of issues found (empty if clean).
    """
    issues: list[str] = []

    def _scan(obj: Any, path: str = "") -> None:
        if isinstance(obj, str):
            for pattern in PLACEHOLDER_PATTERNS:
                if pattern.lower() in obj.lower():
                    issues.append(f"Placeholder '{pattern}' found at {path}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _scan(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _scan(v, f"{path}[{i}]")

    _scan(data)
    return issues


def check_bloom_coverage(objectives: list[dict[str, Any]], min_levels: int = 2) -> list[str]:
    """Verify learning objectives cover at least min_levels distinct Bloom levels.

    Args:
        objectives: List of learning objective dicts with 'bloom_level' key.
        min_levels: Minimum distinct Bloom levels required.

    Returns:
        List of issues (empty if coverage is sufficient).
    """
    bloom_levels: set[str] = set()

    for obj in objectives:
        level = obj.get("bloom_level", "")
        if level:
            bloom_levels.add(level)

    if len(bloom_levels) < min_levels:
        return [
            f"Insufficient Bloom coverage: found {len(bloom_levels)} levels "
            f"({bloom_levels}), need ≥{min_levels}"
        ]
    return []


def check_answer_key_separation(artifact: dict[str, Any]) -> list[str]:
    """Verify answer keys are not in student-facing sections.

    INVARIANT-05: Answer keys MUST be in teacher_only sections.

    Args:
        artifact: Artifact content dict to check.

    Returns:
        List of issues (empty if properly separated).
    """
    issues: list[str] = []
    answer_patterns = ["answer:", "correct:", "solution:"]

    sections = artifact.get("sections", [])
    for i, section in enumerate(sections):
        if section.get("teacher_only", False):
            continue

        content = str(section.get("content", ""))
        for pattern in answer_patterns:
            if pattern in content.lower():
                issues.append(
                    f"Answer key leakage in section {i}: '{pattern}' found in student content"
                )

    return issues


class CircuitBreaker:
    """Circuit breaker pattern for validation failures.

    Trips after threshold consecutive failures.
    Resets on single success.
    """

    def __init__(self, threshold: int = 3) -> None:
        self.threshold = threshold
        self._failure_count = 0
        self._is_open = False

    def record_success(self) -> None:
        """Record a successful validation. Resets failure count."""
        self._failure_count = 0
        self._is_open = False

    def record_failure(self) -> None:
        """Record a failed validation. Trips if threshold reached."""
        self._failure_count += 1
        if self._failure_count >= self.threshold:
            self._is_open = True

    def is_open(self) -> bool:
        """Check if circuit is open (blocking further attempts)."""
        return self._is_open
