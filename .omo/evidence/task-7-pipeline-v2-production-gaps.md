# Task 7 — Prompt Compiler with Overlay Governance and Provenance

## Status: DONE

## What was delivered

### New files

| File | Pure LOC | Purpose |
|------|----------|---------|
| `packages/agents/prompts/compiler.py` | ~195 | PromptCompiler, Overlay, CompiledPrompt, 5 error types, variable extraction/substitution, secret detection, drift gate |
| `packages/agents/prompts/tests/test_compiler.py` | ~300 | 43 tests across 12 test classes covering all required invariants |

### Modified files

| File | Change |
|------|--------|
| `packages/agents/prompts/__init__.py` | Added exports: CompiledPrompt, Overlay, PromptCompiler, MissingVariableError, UnknownVariableError, DuplicateOverlayError, SecretOverlayError |

### Architecture

```
PromptCompiler(registry)
  └─ compile(module_id, variables, overlays, version)
       ├─ 1. Fetch module → drift check (reject DriftRejectionError)
       ├─ 2. Validate overlays (reject DuplicateOverlayError, SecretOverlayError)
       ├─ 3. Extract {{vars}} from body → validate (reject MissingVariableError, UnknownVariableError)
       ├─ 4. Substitute variables into body
       ├─ 5. Sort overlays by (order, id) → join deterministically
       └─ 6. Build PromptMetadata → return CompiledPrompt
```

### Key design decisions

1. **Variable syntax**: `{{variable_name}}` — regex `\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}` — only valid identifiers treated as variables; unclosed `{{` treated as literal
2. **Overlay ordering**: Deterministic sort by `(order, id)` tuple — same overlays in any input order produce identical output
3. **Overlay body is literal**: No variable substitution in overlay content — only the module body gets substitution
4. **Secret detection**: Mirrors `prompt_gate.py` regex (Bearer, api_key, secret, token, password, sk/pk/rk/xoxb/ghp/github_pat patterns)
5. **Drift gate**: Uses `detect_drift()` from `drift.py` — any hash mismatch or un-bumped version blocks compilation
6. **Provenance**: Emits `PromptMetadata` via `build_prompt_metadata()` — compiled_hash is SHA-256 of the final compiled body
7. **No ad-hoc string concatenation**: All assembly uses `str.join` or `re.sub`
8. **Typed everything**: All error types, Overlay, CompiledPrompt are frozen dataclass(slots=True) — no Any/object annotations

## Test coverage

43 tests in `test_compiler.py`:

| Class | Count | Covers |
|-------|-------|--------|
| TestOverlayContract | 4 | frozen, slotted, defaults, order |
| TestCompiledPromptContract | 2 | frozen, empty overlay_ids default |
| TestCompilerErrorContracts | 4 | error fields and __str__ |
| TestCompileSuccess | 5 | basic, metadata, version, no-vars, multi-occurrence |
| TestCompiledHash | 2 | SHA-256 match, different-var-different-hash |
| TestOverlayGovernance | 4 | single, multi-sorted, deterministic-order, empty |
| TestVariableValidation | 5 | missing, multi-missing, unknown, multi-unknown, exact-match |
| TestDuplicateOverlayRejection | 2 | duplicate detection, unique-ok |
| TestSecretOverlayRejection | 6 | bearer, api_key, secret, ghp, github_pat, clean-ok |
| TestDriftRejection | 2 | drifted-rejected, clean-not-rejected |
| TestModuleNotFound | 1 | missing module KeyError |
| TestMalformedInput | 4 | unclosed var, empty var, empty overlay body, overlay-no-substitution |
| TestCompileWithVersion | 1 | specific version selection |
| TestDriftIntegration | 1 | detect_drift integration |

## Manual QA results

| Probe | Input | Expected | Actual | Pass |
|-------|-------|----------|--------|------|
| QA1: Judge + safe overlay | judge_v1 + Overlay(safe) | Compiled body with overlay appended | 899 chars, overlay_ids=['safe_ov'] | PASS |
| QA2: Custom module all vars | custom_v1 + 3 vars | All {{vars}} substituted | "Teach Math to grade 5. Use inquiry." | PASS |
| QA3: Secret overlay | Overlay with api_key pattern | SecretOverlayError | Raised: "Secret-like content in overlay 'bad'" | PASS |
| QA4: Missing variable | custom_v1 + 1/3 vars | MissingVariableError | Raised: "Missing variables: grade, method" | PASS |
| QA5: Unknown variable | custom_v1 + extra var | UnknownVariableError | Raised: "Unknown variables: extra" | PASS |
| QA6: Duplicate overlay | 2 overlays with same id | DuplicateOverlayError | Raised: "Duplicate overlay id: 'same'" | PASS |
| QA7: Dirty worktree (drift) | Tampered planner body | DriftRejectionError | Raised with hash mismatch + unbumped version | PASS |

## Lint results

- ruff: All checks passed on compiler.py, __init__.py, test_compiler.py
- pytest: 101 passed (43 compiler + 58 existing registry/drift/metadata)
- No ad-hoc string concatenation in compiler.py
- No Any/object annotations
- All files under 250 pure LOC

## Known limitations

1. Secret regex uses `ghp-` (dash) not `ghp_` (underscore) — matches prompt_gate.py behavior. Real GitHub PATs use underscore format; a broader regex would catch both.
2. Overlay bodies are not variable-substituted — this is by design (overlays are literal content).
3. No repo-wide caller migration — task 8 handles scoped caller metadata integration.
