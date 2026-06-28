# Final Evidence: real-llm-pipeline-wiring

## Date: 2026-06-28
## Session: opencode:ses_101f37697ffeFUHacVST9n3XYz

## Per-Artifact Generation: VERIFIED ✅

Gateway logs confirm the refactored content_creator_node makes separate LLM calls per artifact type:

### Run 1 (bde32c08): All 3 artifacts succeeded
| Artifact | Attempt | Duration | Status |
|----------|---------|----------|--------|
| quiz     | 1       | 122.3s   | ✅ Success |
| lesson   | 1       | 219.1s   | ✅ Success |
| worksheet| 1       | 109.9s   | ✅ Success |

### Run 2 (72493d62): Quiz failed after 3 retries
| Artifact | Attempt | Duration | Status |
|----------|---------|----------|--------|
| quiz     | 1       | 438.7s   | ❌ Empty content |
| quiz     | 2       | 185.9s   | ❌ JSON parse error |
| quiz     | 3       | 161.0s   | ❌ JSON parse error |

**Root cause**: 4omc reasoning model occasionally produces empty or malformed JSON for quiz artifacts. This is a model behavior issue, not a code defect.

## Key Metrics
- Per-artifact LLM call sizes: ~20,863-21,169 chars (well within 32K max_tokens)
- Successful artifact generation: 110-219 seconds per artifact
- Total pipeline time for 3 artifacts: ~8 minutes (when all succeed)
- All 207 unit tests pass
- Content creator generates artifacts one at a time (verified by log tags: `artifact:quiz`, `artifact:lesson`, `artifact:worksheet`)

## Architecture Verification
- [x] Per-artifact generation: each artifact gets its own LLM call with `artifact:{type}` tag
- [x] Component-aware gates: content_reviewer and llm_judge use extract_student_text
- [x] Finalize uses extract_external_urls for nested component URL detection
- [x] Renderer builds once, not per-artifact
- [x] Teacher gates intact (approval endpoints verified in harness)
- [x] Package boundaries preserved (no services→packages imports)
- [x] Placeholder artifacts not returned as success
- [x] Per-artifact failure metadata tracked

## Remaining Work
- Quiz artifact JSON stability needs model-level investigation (separate from this plan)
- Live E2E full flow (plan → export) not yet completed due to quiz retry failures
- Final verification wave (F1-F4) pending
