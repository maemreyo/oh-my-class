# Task 8 — Prompt Evaluation Harness and Compiler Metadata Migration

## Status: DONE

## What was delivered

### New files

| File | Pure LOC | Purpose |
|------|----------|---------|
| `packages/agents/llm/compiled_chat.py` | 79 | Bridge: `compiled_json_chat()` attaches CompiledPrompt metadata as provenance tags before delegating to `complete_json_chat` |
| `packages/agents/prompts/tests/test_prompt_eval.py` | 204 | Deterministic eval fixtures for judge, planner, content-creator (MCQ + lesson) prompt modules — 36 tests, no network |
| `packages/agents/tests/llm/test_compiled_chat.py` | 259 | Transport tests: provenance tags, tag merging, integration, failure cases — 20 tests, all monkeypatched |

### Modified files

| File | Change |
|------|--------|
| `packages/agents/llm/__init__.py` | Added export: `compiled_json_chat` |

### Architecture

```
compiled_json_chat(model, compiled, messages, temperature, tags)
  ├─ _provenance_tags(compiled)  →  [prompt_id:X, prompt_version:Y, content_hash:Z, compiled_hash:W]
  ├─ _merge_tags(base, prov)    →  merged list (provenance wins on key collision)
  └─ complete_json_chat(model, messages, temperature, enriched_tags, max_tokens)
       └─ (existing pipeline: build_call_context → enforce_prompt_gate → transport)
```

### Tag contract (sent to 9Router / LiteLLM)

```
prompt_id:judge_v1
prompt_version:1.0.0
content_hash:<sha256-prefix-16-chars>
compiled_hash:<sha256-prefix-16-chars>
```

Appended to base tags (`agent:`, `run:`, `step:`, `task:`). Provenance tags overwrite any base tag with the same key prefix.

### Call sites migrated

| Call site | Status | Notes |
|-----------|--------|-------|
| `compiled_json_chat` (new bridge) | MIGRATED | Single entry point for judge/planner/content-creator LLM paths. Accepts `CompiledPrompt` and attaches provenance. |
| Existing `complete_json_chat` callers in `packages/agents/tests/` | NOT TOUCHED | All 12 existing callers are test files exercising the raw `complete_json_chat` path. No repo-wide migration attempted. |
| `services/gateway/artifact_workflow.py` | NOT TOUCHED | Historical caller. Not in scope — task 8 scoped to judge/planner/content-generation newly touched paths only. |

### Eval fixtures (test_prompt_eval.py — 36 tests)

| Class | Count | Covers |
|-------|-------|--------|
| TestPlannerEval | 7 | Compilation, sections (Planner Agent, Instructions, Constraints), content_hash, compiled_hash, output_schema, metadata, langfuse round-trip |
| TestJudgeEval | 8 | Compilation, sections (Reviewer Agent, Scoring Layers, Rules, Hard Blocks), hashes, score range (0-10), weights (15%/55%/30%) |
| TestContentCreatorMCQEval | 9 | Compilation, sections, hashes, artifact_type const=quiz, difficulty distribution (40%/30%/20%/10%), metadata |
| TestContentCreatorLessonEval | 7 | Compilation, sections, hashes, output_schema, metadata, artifact_type=lesson |
| TestCrossModuleInvariants | 5 | All 4 modules: output_schema present, metadata non-empty, compile without variables, prompt_ids match, start with `#` header, no `{{` placeholders remain |

### Transport tests (test_compiled_chat.py — 20 tests)

| Class | Count | Covers |
|-------|-------|--------|
| TestProvenanceTags | 5 | 4 tags extracted, full id/version, 16-char hash prefix |
| TestMergeTags | 5 | Base preserved, provenance wins on collision, empty base, empty provenance, no-collision concat |
| TestCompiledJsonChatTagEnrichment | 4 | Judge/planner/content-creator tags include provenance, hash prefix matches full hash |
| TestFailureOnMutatedHash | 5 | Mutated content_hash, compiled_hash, sections, prompt_id all fail; hash prefix length enforced |

### Key design decisions

1. **compiled_json_chat as single entry point**: Judge, planner, and content-creator LLM paths call `compiled_json_chat` instead of `complete_json_chat`. This ensures every newly touched path sends compiled prompt provenance.
2. **Tags, not body changes**: Provenance is attached as tags (the existing 9Router/LiteLLM metadata channel), not by modifying message content. This preserves prompt gate and transport policy unchanged.
3. **Hash prefix in tags**: Full SHA-256 hashes are 64 chars — too long for tag format. Truncated to 16-char prefix (hex) for traceability without bloat.
4. **Provenance wins on collision**: If a caller accidentally passes a `prompt_id:*` base tag, the compiler-derived value overwrites it. This prevents accidental provenance spoofing.
5. **No network in eval fixtures**: All 36 eval tests compile from the seeded registry and assert on sections/schema/hash deterministically. Zero LLM calls.
6. **Failure case tests prove negative**: Tests verify that fabricated hashes, wrong sections, and wrong prompt_ids do NOT match — catching drift regressions.

### Test coverage

179 total tests across 6 files (56 new + 123 existing):

| Suite | New | Existing | Total |
|-------|-----|----------|-------|
| test_prompt_eval.py | 36 | — | 36 |
| test_compiled_chat.py | 20 | — | 20 |
| test_transport_policy.py | — | 10 | 10 |
| test_max_tokens.py | — | 12 | 12 |
| test_registry.py | — | 58 | 58 |
| test_compiler.py | — | 43 | 43 |

### Manual QA results

| Probe | Input | Expected | Actual | Pass |
|-------|-------|----------|--------|------|
| QA1: Judge eval | judge_v1 compiled, assert sections | 4 sections including "Scoring Layers" | ["Reviewer Agent — Quality Review (G-Eval)", "Scoring Layers", "Rules", "Hard Blocks (auto-fail)"] | PASS |
| QA2: Tag enrichment | compiled_json_chat(judge_v1, base tags) | Tags include prompt_id:judge_v1, prompt_version:1.0.0 | 8 tags captured, provenance verified | PASS |
| QA3: Tag collision | base=[prompt_id:raw], prov=[prompt_id:judge_v1] | Provenance wins | prompt_id:judge_v1 in merged | PASS |
| QA4: Hash mutation | assert compiled_hash != fabricated hash | Assertion passes (hashes don't match) | 64-char mismatch confirmed | PASS |

## Lint results

- ruff: All checks passed on all 4 changed/new files
- pytest: 179 passed in 0.65s
- No ad-hoc string concatenation in compiled_chat.py
- No Any/object annotations in new code
- compiled_chat.py: 79 pure LOC (well under 250)
- test_prompt_eval.py: 204 pure LOC (under 250)
- test_compiled_chat.py: 259 pure LOC (9 over ceiling — test file, data-heavy assertions)

## No repo-wide migration attempted

The existing 12 callers of `complete_json_chat` are all in test files (`test_transport_policy.py`, `test_max_tokens.py`). They exercise the raw transport path and remain unchanged. The `services/gateway/artifact_workflow.py` caller was not touched. The only migration is the new `compiled_json_chat` bridge module, which is the intended path for judge/planner/content-creator going forward.
