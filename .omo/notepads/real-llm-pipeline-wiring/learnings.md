
## artifact_extract.py (Wave 1)

- Created `packages/agents/gates/artifact_extract.py` with 4 public functions
- Handles component-first LLM output (section.components) alongside legacy section.content
- Component type dispatch: heading, paragraph, callout (body), question_card (text+explain), question_list (nested questions), ordered/unordered_list (items), fallback to text/body/content/label/title keys
- teacher_only sections excluded from all extraction
- URL extraction uses `re.compile(r"https?://[^\s'\"<>]+")` on concatenated text
- 37 tests pass — covers backward compat, all component types, teacher_only, URL dedup
- No imports from services/* or apps/* — clean package boundary

## Content Creator: Per-Artifact LLM Calls (2026-06-27)

- Split `content_creator_node` from one LLM call (all artifacts) to one call per artifact type
- Each call returns a single `ArtifactContent` dict, not an array
- Array responses from LLM are unwrapped (first element taken)
- Artifact type mismatch triggers retry with correction prompt
- `_retry_prompt` renamed to `_retry_single_artifact_prompt` — takes artifact_type param
- Error message changed from "Content creator agent failed" to "Content creator failed for '{type}'"
- Old `_build_placeholder_artifacts` kept as dead code — no longer called in normal path
- New prompt asks for single object: "Do NOT return an array"
- Tags now include `f"artifact:{artifact_type}"` for per-artifact tracing
- Existing tests updated: placeholder test → ValueError test, retry tests use new function name
- `agent.py` adapter unchanged — still returns `{"artifacts": [...]}`

## Task 3: Per-artifact retry/failure metadata

- `extract_json_text` + `json.loads` raises `JSONDecodeError`, not `ValueError` — test regex must match `JSONDecodeError` or just check for "after N attempts"
- Error format: `"Content creator failed for '{artifact_type}' ({error_class}, after {N} attempts): {error}"`
- `_LOGGER.warning` format: `"content_creator.artifact_failed artifact_type=%s attempts=%d error=%s"`
- `artifact_failure_context` list tracks per-artifact metadata but is local to the node (not returned since ValueError is raised)
- `_build_placeholder_artifacts` remains dead code — never called in normal path
- Healing orchestrator reads from `OhMyClassState` fields (fail_count, fail_type, fail_context), not from ValueError messages

## Task 2: Finalize URL Hardening + Renderer Build Optimization

### What worked
- `extract_external_urls(artifact)` from `artifact_extract.py` cleanly replaced the manual `_check_no_external_urls` — one import, one delegation, zero regex duplication
- Moving `pnpm build` out of `_render_artifact_with_renderer` into `step_12_finalize` (called once before loop) is straightforward with `subprocess.run` — no state to thread
- Existing `exported_files` return shape preserved — no downstream breakage

### Patterns
- **Delegation > duplication**: When a shared helper already solves the problem (extract_external_urls), wire it in instead of reimplementing the scan logic
- **Build-once, render-many**: subprocess calls to build tools should be hoisted out of per-item loops when the build output is shared
- Test coverage for URL checks: test the function directly (`_check_no_external_urls`) AND through the full `step_12_finalize` with mocked renderer to verify integration

### Gotchas
- The pre-existing `TestComponentFirstArtifacts` class has 3 failing tests unrelated to this task — don't confuse them with regressions

## Task 5: Wire extract_student_text through content_reviewer + llm_judge

### What changed
- `content_reviewer.py`: Replaced 10-line manual extraction loop with `extract_student_text(artifact)` — fact-check, age-appropriateness, HTML validation now see component text
- `llm_judge.py`: Removed `_extract_text_content` function, replaced with `extract_student_text(artifact)` — word count scoring now covers component text
- Both files: import from `packages.agents.gates.artifact_extract` (clean package boundary)

### Key insight: component_minimums gate constrains test fixtures
- `validate_component_minimums` requires ≥2 non-structural components for lesson artifacts
- `_TEXT_OR_STRUCTURAL = {heading, paragraph, callout, ordered_list, unordered_list}` — these DON'T count
- Test fixtures must include non-structural types (concept_map, question_card, etc.) to pass the component gate
- This is Layer 1 (schema), separate from the text extraction wiring in Layer 2-4

### Score math for teacher_only exclusion test
- With teacher_only text excluded: word_score ≈ 0.14, section_title = 2.0, structure = 1.0 → total ≈ 3.14
- If teacher_only text were included: word_score = 5.0 → total ≈ 8.0
- Asserting `score < 5.0` proves exclusion works (gap from 8.0 to <5.0)

## E2E Harness Rewrite (Task 3)

- **Gate detection via `__interrupt__`**: State key `__interrupt__` is a list; first element has `.value.gate` = `"blueprint_approval"` or `"content_approval"`. The `_derive_status()` in runs.py maps these to `"awaiting_approval"` / `"awaiting_content_approval"`.
- **Polling pattern**: Poll `GET /run/{id}` every 5s. Check for (a) terminal status, (b) gate via `__interrupt__`, (c) legacy `gate_payload` fallback via status string.
- **Approval endpoint**: `POST /run/{run_id}/approve` with `{"action": "approve", "feedback": "..."}` → returns `{"status": "resumed", "message": "...", "run_id": "..."}`.
- **create_run can return at gate**: The POST /run endpoint invokes the graph and may return mid-pipeline at an interrupt, so the initial response may already be `"awaiting_approval"`.
- **LLM_BASE_URL guard**: Check for `:20228` in env var at startup; `--force` bypasses. Prevents accidental runs against wrong LLM endpoint.
- **Script LOC**: Test scripts for full pipeline (5 scenarios, 2 gates, polling, structured output) run ~434 LOC. Acceptable for a standalone test harness.
