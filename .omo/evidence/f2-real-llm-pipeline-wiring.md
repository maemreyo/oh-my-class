# F2: Code Quality Review

**Plan**: `real-llm-pipeline-wiring`
**Reviewer**: f.light
**Date**: 2026-06-30
**Scope**: 13 changed files across `packages/agents` and `services/gateway`

---

## Verdict: APPROVE

All quality gates pass. The implementation demonstrates solid engineering practices with bounded retries, proper error handling, and fail-closed placeholder behavior.

---

## Package Boundaries

**Status**: PASS

- `packages/agents/sub_agents/content_creator/nodes.py` → imports only from `common.contracts.*`, `packages.agents.*`
- `packages/agents/gates/*.py` → imports only from `packages.agents.*`, `packages.quality.*`
- `packages/agents/nodes/finalize.py` → imports from `packages.agents.*`
- `services/gateway/teaching_pack_snapshot_store.py` → imports only from `services.gateway.*`
- Zero cross-boundary violations found via grep

```bash
$ grep -r "from services\.\|from apps\." packages/agents/ packages/quality/
# No matches
```

---

## Retry Logic

**Status**: PASS

### Per-Artifact Retries (`content_creator_node`)
- **Max attempts**: 3 per artifact type (hardcoded `range(3)`)
- **Bounded**: Yes — loop terminates after 3 attempts
- **Failure metadata captured**: `artifact_type`, `attempts`, `error_class`, `last_error`
- **On failure**: Raises `ValueError` with descriptive message including artifact type, error class, and attempt count
- **No silent failures**: All exceptions logged via `_LOGGER.warning()` and `log_llm_failure()`

### Healing Orchestrator
- **Max retries**: 3 (configurable via `GateConfig.max_retries`)
- **Escalation**: Routes to `escalate_node` after max retries
- **Placeholder detection**: Lines 58-60 detect placeholder artifacts and force escalation

---

## Prompt Sizing

**Status**: PASS

### System Prompt (`system.md`)
- Comprehensive but well-structured: ~350 lines
- Sections: Role, Output Format, Hard Constraints, RCM, Component Catalog, Methodology rules
- Token estimate: ~2500-3000 tokens (within reasonable limits)

### User Prompt (`prompt_contract.py`)
- `build_single_artifact_prompt`: Includes truncated summaries + artifact-specific guidance
- `retry_single_artifact_prompt`: Caps `last_content` to 3000 chars, `error` to 1200 chars

### Summarizer Truncation (`summarizers.py`)
| Data | Limit | Truncation |
|------|-------|------------|
| Learning objectives | 6 max | 180 chars each |
| Learning plan phases | 9 max | 120 chars each |
| Assessment checkpoints | 4 max | 160 chars each |
| Verified sources | 5 max | 120 chars each |
| Key findings | 3 max | 220 chars each |

**Total prompt budget**: System (~3K tokens) + User (~2-4K tokens) = **~5-7K tokens** — well within model context windows.

---

## Placeholder Fail-Closed

**Status**: PASS

### Implementation
1. `_build_placeholder_artifacts()` exists in `nodes.py` (lines 209-234) with `metadata={"placeholder": True}`
2. **NOT called** in `content_creator_node()` — the function raises `ValueError` on failure
3. `healing/orchestrator.py` line 59: Detects placeholders and routes to escalation

### Evidence
```python
# nodes.py:166 — On failure, raises ValueError (not placeholder)
raise ValueError(
    f"Content creator failed for '{artifact_type}' "
    f"({error_class}, after {attempt_number} attempts): "
    f"{parse_err}",
) from parse_err
```

### Test Confirmation
```python
# test_content_creator_per_artifact.py:214
"""If one artifact fails all retries, ValueError is raised (not placeholder)."""
async def test_all_retries_exhausted_raises_value_error(self):
    ...
    with pytest.raises(ValueError, match="Content creator failed for 'lesson'"):
        await content_creator_node(state)
```

### Recovery Path
- Placeholder function is "kept for emergency use" but currently dead code
- Healing orchestrator detects and escalates any placeholder artifacts
- Schema validator would reject placeholders with invalid structure

---

## Type Safety

**Status**: PASS (with justification)

### Python `# type: ignore` in Changed Files
| File | Line | Justification |
|------|------|---------------|
| `nodes.py` | 215 | `artifact_type=atype` — `atype` is `str` but `ArtifactContent` expects `Literal[...]`. In dead code path (placeholder function). |

### No New Type Ignores Added
- All other `# type: ignore` in `packages/agents/` are pre-existing
- No new `# type: ignore` introduced by this plan

### TypeScript
- No TypeScript files were modified in this plan
- No `as any` found in gateway test files

---

## Error Handling

**Status**: PASS

### Exception Handling Patterns
1. **Specific catches**: `except (ValueError, json.JSONDecodeError)` for parse errors
2. **Catch-all with re-raise**: `except Exception as e` → re-raises as `ValueError` with context
3. **No bare `except:`**: Verified via grep (0 matches in `packages/agents/`)
4. **Exception chaining**: `from parse_err` / `from e` preserves original traceback
5. **Logging**: Every failure path logs via `_LOGGER.warning()` and `log_llm_failure()`

### Subprocess Handling (`finalize.py`)
- `subprocess.run(..., check=True)` — raises `CalledProcessError` on failure
- No try/except around subprocess calls — failures propagate to graph error handling

---

## Test Quality

**Status**: PASS

### `test_content_creator_per_artifact.py` (13 test methods)
| Test Class | What It Verifies |
|------------|------------------|
| `TestPerArtifactCallCount` | 3 artifact types → 3 LLM calls |
| `TestPerArtifactPromptTargets` | Each prompt contains only target type |
| `TestOutputOrderMatchesInput` | Output order matches input order |
| `TestArrayResponseUnwrap` | Array response unwraps first element |
| `TestArtifactTypeMismatchRetry` | Wrong type triggers retry |
| `TestSingleArtifactFailureRaisesValueError` | Failure raises, not placeholder |
| `TestBuildSingleArtifactPrompt` | Prompt builder correctness |
| `TestFailureMetadataInError` | Error messages include context |
| `TestMixedSuccessFailure` | Partial success handling |
| `TestRetryRecovery` | Recovery after intermediate failures |

**Quality indicators**:
- Tests assert real behavior (call counts, output shapes, error messages)
- Tests use mock LLM responses with specific failure scenarios
- Tests verify retry semantics (attempt counts, error propagation)
- No trivially passing tests

### `test_teaching_pack_previews.py` (7 test methods)
- Integration tests against real PostgreSQL database
- Verifies answer key isolation (INVARIANT-05)
- Verifies XSS protection (HTML entity escaping)
- Verifies access control (non-owner → 404)
- Verifies status code correctness (200, 409, 422)

### `test_content_creator_prompt_pedagogy.py` (1 test method)
- Verifies Present Tenses methodology content exists in prompt
- Could be more robust but provides basic regression protection

---

## Code Style

**Status**: PASS

### Patterns Followed
- LangGraph node functions: `(state) → partial_state`
- Pydantic v2 models for validation
- pytest class-based tests with descriptive names
- Consistent naming conventions (`step_XX_*` for graph nodes)

### Documentation
- All public functions have docstrings
- Complex logic has inline comments
- Module-level docstrings present

### Code Organization
- Separation of concerns: prompts, summarizers, validators in separate modules
- Lazy imports in node functions (avoids circular dependencies)
- Constants defined at module level (`_JSON_ONLY_SUFFIX`, `REQUIRED_ARTIFACT_KEYS`)

---

## Summary

| Check | Result | Notes |
|-------|--------|-------|
| Package Boundaries | ✅ PASS | Zero cross-boundary imports |
| Retry Logic | ✅ PASS | Bounded (max 3), metadata captured, no silent failures |
| Prompt Sizing | ✅ PASS | Summaries truncated, total ~5-7K tokens |
| Placeholder Fail-Closed | ✅ PASS | Failures raise ValueError, not placeholder |
| Type Safety | ✅ PASS | Existing ignores justified, no new ones added |
| Error Handling | ✅ PASS | Specific catches, proper chaining, logging |
| Test Quality | ✅ PASS | Real assertions, no trivial tests |
| Code Style | ✅ PASS | Follows existing patterns |

### Optional Future Considerations (not blockers)
1. `_build_placeholder_artifacts()` is dead code — could be removed in future cleanup
2. `test_content_creator_prompt_pedagogy.py` could assert more prompt invariants

---

**Approver**: f.light
**Confidence**: High
**Risk**: Low
