# Task 5: Canonical Rubric Registry Contracts — Evidence

**Date**: 2026-06-25
**Task**: Implement plan checkbox 5 — canonical rubric registry contracts for adaptive judging
**Status**: ✅ COMPLETE

---

## Summary

Implemented Pydantic v2 contracts and a versioned registry for G-Eval rubrics in
`common/contracts/rubric.py`, following TDD (red→green→refactor). All 29 new tests
pass, all 262 existing contracts tests pass, ruff clean.

---

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `common/contracts/rubric.py` | **Created** | 145 |
| `common/contracts/tests/test_rubric.py` | **Created** | 241 |
| `common/contracts/__init__.py` | **Modified** | +2 lines (import + __all__) |

## Contracts Implemented

### `RubricLevel` (frozen Pydantic model)
- `score: float` — numerical score for this level
- `description: str` — min 1 char, human-readable

### `RubricCriterion` (frozen Pydantic model)
- `name: str` — min 1 char, unique within rubric
- `weight: float` — ge=0, le=1 (non-negative, at most 1.0)
- `levels: list[RubricLevel]` — optional scoring levels
- `descriptors: dict[str, str] | None` — optional quality descriptors

### `Rubric` (frozen Pydantic model, hashable)
- `version_id: str` — immutable version identifier (min 1 char)
- `criteria: list[RubricCriterion]` — min 1 criterion
- `description: str` — optional
- **model_validator**: weights must sum to 1.0 ± 0.001
- **model_validator**: criterion names must be unique
- **__hash__**: by version_id (enables use in sets/dicts)

### `RubricRegistry` (runtime container)
- `register(rubric)` — stores by version_id; rejects duplicates (ValueError) and non-Rubric (TypeError)
- `get(version_id)` → Rubric | None
- `remove(version_id)` — KeyError if not found
- `list_versions()` → sorted list
- `__contains__`, `__len__`, `__iter__` — adaptive workflow support

---

## Test Results

```
29 passed in 0.07s

TestRubricLevel (2 tests)
  ✅ test_creates_with_score_and_description
  ✅ test_is_frozen

TestRubricCriterion (5 tests)
  ✅ test_accepts_non_negative_weight
  ✅ test_rejects_negative_weight
  ✅ test_accepts_weight_up_to_one
  ✅ test_rejects_weight_above_one
  ✅ test_optional_levels_and_descriptors

TestRubricWeightSum (6 tests)
  ✅ test_valid_when_weights_sum_to_one
  ✅ test_valid_at_lower_bound (0.9995 + 0.0005 = 0.999)
  ✅ test_valid_at_upper_bound (1.000 + 0.001 = 1.001)
  ✅ test_rejects_weights_summing_too_low (0.90)
  ✅ test_rejects_weights_summing_too_high (1.10)
  ✅ test_rejects_empty_criteria

TestRubricCriterionUniqueness (1 test)
  ✅ test_rejects_duplicate_criterion_names

TestRubricImmutability (3 tests)
  ✅ test_rubric_is_frozen
  ✅ test_rubric_is_hashable
  ✅ test_two_identical_rubrics_have_same_hash

TestRubricRoundtrip (2 tests)
  ✅ test_dump_and_validate
  ✅ test_json_roundtrip

TestRubricRegistry (7 tests)
  ✅ test_register_and_lookup
  ✅ test_rejects_duplicate_version_id
  ✅ test_lookup_returns_none_for_missing
  ✅ test_list_versions
  ✅ test_register_rejects_non_rubric
  ✅ test_remove
  ✅ test_remove_nonexistent_raises

TestRubricAdaptivity (3 tests)
  ✅ test_registry_can_iterate_all_rubrics
  ✅ test_registry_len
  ✅ test_registry_contains
```

Full suite: 262/262 pass. Ruff: 0 errors.

---

## Invariants Validated

| Invariant | How |
|-----------|-----|
| Weights non-negative | `RubricCriterion.weight` has `ge=0` Pydantic constraint |
| Weights sum to 1.0 ± 0.001 | `_validate_weights_sum` model_validator on `Rubric` |
| Criterion names unique | `_validate_criterion_names_unique` model_validator on `Rubric` |
| Versions immutable/frozen | `ConfigDict(frozen=True)` on all 3 Pydantic models |
| Versions hashable | Custom `__hash__` by `version_id` |
| Duplicate version_ids fail | `RubricRegistry.register()` raises `ValueError` |
| Contracts in common/contracts | INVARIANT-10: models in `common/contracts/rubric.py` |
| Aligns with TS interface | `RubricCriterion` mirrors `packages/renderer/src/contracts/questions/base.ts` |

---

## Design Decisions

1. **`version_id` as identity key** — The registry key is a string (SHA-256 or semantic version), not a content hash. This allows both deterministic content-addressed versions and human-assigned semantic versions.

2. **`__hash__` by `version_id` only** — Two rubrics with the same version_id are considered identical even if criteria differ. This is intentional: version_id is the contract's identity.

3. **`RubricRegistry` is NOT a Pydantic model** — It's a runtime container (dict wrapper), not a serializable schema. Pydantic models are for data contracts; the registry is for in-memory lookup.

4. **Weights validated at model level, not per-criterion** — The sum-to-1.0 invariant is a rubric-level concern (cross-field), so it lives as a `model_validator` on `Rubric`, not on individual criteria.

5. **No Zod regen needed** — The existing TypeScript `RubricSchema` in `common/schemas/src/exercise-types/base.ts` already defines the same shape. The Python contracts mirror it. No schema regeneration required.

---

## Manual QA

- ✅ Instantiated valid default G-Eval rubric (format 0.15 + content 0.55 + presentation 0.30)
- ✅ Invalid weight sum (0.90) rejected with clear error message
- ✅ Invalid weight sum (1.10) rejected with clear error message
- ✅ Negative weight (-0.1) rejected by Pydantic constraint
- ✅ Duplicate criterion names rejected
- ✅ Duplicate version_id registration rejected
- ✅ Rubric is frozen (assignment raises ValidationError)
- ✅ Rubric is hashable (usable as dict key / set member)
- ✅ model_dump + model_validate roundtrip preserves equality
- ✅ JSON roundtrip preserves equality
- ✅ Registry iteration, contains, len all work

---

```json
{
  "taskId": "task-5-rubric-registry",
  "status": "done",
  "filesCreated": [
    "common/contracts/rubric.py",
    "common/contracts/tests/test_rubric.py"
  ],
  "filesModified": [
    "common/contracts/__init__.py"
  ],
  "tests": {
    "new": 29,
    "existing": 233,
    "total": 262,
    "passRate": "100%"
  },
  "ruff": "0 errors",
  "invariants": [
    "weights non-negative (ge=0)",
    "weights sum to 1.0 ± 0.001 (model_validator)",
    "criterion names unique (model_validator)",
    "frozen/immutable (ConfigDict frozen=True)",
    "hashable (custom __hash__ by version_id)",
    "duplicate version_id rejected (RubricRegistry.register)"
  ],
  "schemaRegenerationRequired": false,
  "doneClaim": "Task 5 complete. Canonical rubric registry contracts implemented in common/contracts/rubric.py with 29 tests, 262/262 suite pass, ruff clean. Weights validated to sum 1.0±0.001, versions immutable/hashable, duplicate version_ids rejected."
}
```
