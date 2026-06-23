"""Layer 1 — JSON Schema Validation.

Pydantic v2 validators with self-healing (ModelRetry up to 3 times)
and circuit breaker pattern. Validates required fields, format patterns,
no placeholder content, Bloom coverage, and answer key separation.
"""

from packages.quality.layer1_schema.circuit_breaker import CircuitBreaker as StatefulCircuitBreaker
from packages.quality.layer1_schema.validators import (
    CircuitBreaker,
    PLACEHOLDER_PATTERNS,
    ValidationGateError,
    check_answer_key_separation,
    check_bloom_coverage,
    check_placeholder_content,
    validate_schema,
)

__all__ = [
    "validate_schema",
    "check_placeholder_content",
    "check_bloom_coverage",
    "check_answer_key_separation",
    "CircuitBreaker",
    "StatefulCircuitBreaker",
    "ValidationGateError",
    "PLACEHOLDER_PATTERNS",
]
