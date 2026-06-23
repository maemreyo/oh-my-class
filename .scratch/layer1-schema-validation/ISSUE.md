---
title: "Layer 1: Schema Validation with Pydantic Retry + CircuitBreaker"
status: ready-for-agent
labels: []
created: 2026-06-23
github: 1
---

## What to build

Implement Layer 1 quality gate in `packages/quality/layer1_schema/validators.py`. The file already exists with stubs (lines 34-111). Replace the TODO stubs with working implementations.

## Current State

```python
# packages/quality/layer1_schema/validators.py
# Lines 34-66: validate_schema() — stub raising NotImplementedError
# Lines 69-80: check_placeholder_content() — empty implementation
# Lines 83-95: check_bloom_coverage() — empty implementation
# Lines 98-111: check_answer_key_separation() — empty implementation
```

## Implementation Spec

### 1. `validate_schema()` (lines 34-66)

Replace the stub with:

```python
async def validate_schema(
    data: dict[str, Any],
    schema_model: type[BaseModel],
    *,
    max_retries: int = 3,
) -> BaseModel:
    from pydantic import ValidationError
    
    last_error = None
    for attempt in range(max_retries):
        try:
            return schema_model.model_validate(data)
        except ValidationError as e:
            last_error = e
            if attempt < max_retries - 1:
                # ModelRetry: in real implementation, this feeds error back to LLM
                # For now, log and continue
                continue
    raise ValidationGateError(
        layer=1,
        issues=[str(last_error)]
    )
```

### 2. `check_placeholder_content()` (lines 69-80)

Replace with recursive string scanner:

```python
def check_placeholder_content(data: dict[str, Any]) -> list[str]:
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
```

### 3. `check_bloom_coverage()` (lines 83-95)

Replace with:

```python
def check_bloom_coverage(objectives: list[dict[str, Any]], min_levels: int = 2) -> list[str]:
    issues: list[str] = []
    bloom_levels = set()
    
    for obj in objectives:
        level = obj.get("bloom_level", "")
        if level:
            bloom_levels.add(level)
    
    if len(bloom_levels) < min_levels:
        issues.append(
            f"Insufficient Bloom coverage: found {len(bloom_levels)} levels "
            f"({bloom_levels}), need ≥{min_levels}"
        )
    
    return issues
```

### 4. `check_answer_key_separation()` (lines 98-111)

Replace with:

```python
def check_answer_key_separation(artifact: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    
    # Check if answer key patterns exist in student-facing sections
    sections = artifact.get("sections", [])
    for i, section in enumerate(sections):
        # Skip teacher_only sections
        if section.get("teacher_only", False):
            continue
        
        content = str(section.get("content", ""))
        # Check for answer key indicators
        answer_patterns = ["answer:", "correct:", "solution:"]
        for pattern in answer_patterns:
            if pattern in content.lower():
                issues.append(
                    f"Answer key leakage in section {i}: '{pattern}' found in student content"
                )
    
    return issues
```

### 5. Add `CircuitBreaker` class (new, after line 111)

```python
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
```

## Acceptance criteria

- [ ] `validate_schema()` validates Pydantic models with retry logic
- [ ] `validate_schema()` raises `ValidationGateError` after max_retries
- [ ] `check_placeholder_content()` catches `[TBD]`, `TODO`, `lorem ipsum`, `PLACEHOLDER`, `[INSERT`
- [ ] `check_placeholder_content()` recursively scans nested dicts/lists
- [ ] `check_bloom_coverage()` counts distinct bloom_level values
- [ ] `check_bloom_coverage()` returns issue if < min_levels distinct levels
- [ ] `check_answer_key_separation()` skips `teacher_only=True` sections
- [ ] `check_answer_key_separation()` detects answer patterns in student sections
- [ ] `CircuitBreaker.record_success()` resets failure count
- [ ] `CircuitBreaker.record_failure()` increments count
- [ ] `CircuitBreaker.is_open()` returns True after threshold failures

## Test suite

Create `packages/quality/layer1_schema/tests/test_validators.py`:

```python
import pytest
from packages.quality.layer1_schema.validators import (
    validate_schema,
    check_placeholder_content,
    check_bloom_coverage,
    check_answer_key_separation,
    CircuitBreaker,
    ValidationGateError,
    PLACEHOLDER_PATTERNS,
)
from common.contracts.lesson_plan import LessonPlan

class TestValidateSchema:
    @pytest.mark.asyncio
    async def test_valid_schema_passes(self):
        data = {
            "topic": "Photosynthesis",
            "grade_level": "Grade 5",
            "subject": "science",
            "duration_minutes": 45,
            "learning_objectives": [
                {"description": "Understand photosynthesis", "bloom_level": "understand"},
                {"description": "Apply knowledge", "bloom_level": "apply"},
            ],
        }
        result = await validate_schema(data, LessonPlan)
        assert isinstance(result, LessonPlan)
        assert result.topic == "Photosynthesis"
    
    @pytest.mark.asyncio
    async def test_invalid_schema_retries_then_fails(self):
        data = {"topic": ""}  # Missing required fields
        with pytest.raises(ValidationGateError) as exc_info:
            await validate_schema(data, LessonPlan, max_retries=2)
        assert exc_info.value.layer == 1
        assert len(exc_info.value.issues) > 0

class TestCheckPlaceholderContent:
    def test_catches_tbd(self):
        data = {"title": "Lesson [TBD]"}
        issues = check_placeholder_content(data)
        assert any("[TBD]" in i for i in issues)
    
    def test_catches_todo(self):
        data = {"description": "TODO: add content"}
        issues = check_placeholder_content(data)
        assert any("TODO" in i for i in issues)
    
    def test_catches_nested(self):
        data = {"sections": [{"content": "lorem ipsum"}]}
        issues = check_placeholder_content(data)
        assert any("lorem ipsum" in i for i in issues)
    
    def test_clean_data_passes(self):
        data = {"title": "Real Content"}
        issues = check_placeholder_content(data)
        assert len(issues) == 0

class TestCheckBloomCoverage:
    def test_sufficient_coverage(self):
        objectives = [
            {"bloom_level": "remember"},
            {"bloom_level": "apply"},
        ]
        issues = check_bloom_coverage(objectives)
        assert len(issues) == 0
    
    def test_insufficient_coverage(self):
        objectives = [
            {"bloom_level": "remember"},
            {"bloom_level": "remember"},
        ]
        issues = check_bloom_coverage(objectives)
        assert len(issues) == 1
        assert "Insufficient" in issues[0]

class TestCheckAnswerKeySeparation:
    def test_answer_in_student_section(self):
        artifact = {
            "sections": [
                {"content": "What is 2+2? Answer: 4", "teacher_only": False}
            ]
        }
        issues = check_answer_key_separation(artifact)
        assert len(issues) == 1
        assert "Answer key leakage" in issues[0]
    
    def test_answer_in_teacher_section_ok(self):
        artifact = {
            "sections": [
                {"content": "Answer: 4", "teacher_only": True}
            ]
        }
        issues = check_answer_key_separation(artifact)
        assert len(issues) == 0

class TestCircuitBreaker:
    def test_trips_after_threshold(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open()
        cb.record_failure()
        assert cb.is_open()
    
    def test_resets_on_success(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert not cb.is_open()
        assert cb._failure_count == 0
```

## File paths

| File | Action |
|------|--------|
| `packages/quality/layer1_schema/validators.py` | MODIFY: Replace stubs (lines 34-111), add CircuitBreaker |
| `packages/quality/layer1_schema/__init__.py` | MODIFY: Add exports |
| `packages/quality/layer1_schema/tests/test_validators.py` | CREATE: Full test suite |

## Dependencies

- `common/contracts/lesson_plan.py` — LessonPlan schema (already exists)
- `pydantic` — ValidationError (already installed)

## Edge cases to handle

1. Empty dict → ValidationGateError
2. None values in nested fields → skip gracefully
3. Unicode placeholder patterns → case-insensitive matching
4. CircuitBreaker with threshold=1 → trips on first failure
