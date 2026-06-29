# Evidence: task 6 - final verification and manual surface QA

## Verification commands
- `uv run pytest packages/agents/tests/sub_agents/test_content_creator.py packages/agents/tests/sub_agents/test_content_creator_component_prompt.py packages/agents/tests/sub_agents/test_content_creator_prompt_size.py packages/agents/tests/sub_agents/test_content_creator_per_artifact.py tests/e2e/test_teaching_pack_component_driven_flow.py -q` -> `73 passed` after preserving legacy prompt-helper test imports.
- `uv run basedpyright tests/e2e/rich_teaching_pack_fixtures.py tests/e2e/test_teaching_pack_component_driven_flow.py` -> `0 errors, 0 warnings, 0 notes` after post-review type-safety fixes.
- `uv run python -m py_compile tests/e2e/rich_teaching_pack_fixtures.py tests/e2e/test_teaching_pack_component_driven_flow.py packages/agents/sub_agents/content_creator/nodes.py packages/agents/sub_agents/content_creator/prompt_contract.py packages/agents/tests/sub_agents/test_content_creator_component_prompt.py packages/agents/tests/sub_agents/test_content_creator_per_artifact.py` -> passed.
- `pnpm --filter @oh-my-class/renderer test -- agent-renderer --runInBand` -> `15 passed` test files, `240 passed` tests.
- `pnpm --filter @oh-my-class/renderer build` -> passed.
- `GIT_MASTER=1 git diff --check` -> clean.

## Manual surface QA
- Drove rich artifacts through `services.gateway.renderer_adapter.render_artifact_content` for all active artifact types.
- Observed output sizes:
  - lesson: 18075 bytes
  - worksheet: 4956 bytes
  - quiz: 8794 bytes
  - drill: 9846 bytes
  - recap: 4186 bytes
  - infographic: 4141 bytes
- The checked-in E2E additionally asserts exported HTML has `<!DOCTYPE html>`, `oh-my-class`, no external URLs, no student answer-key markers, active artifact class landmarks, and multiple visible content blocks.

## LOC hygiene
- `tests/e2e/rich_teaching_pack_fixtures.py`: 130 pure LOC.
- `tests/e2e/test_teaching_pack_component_driven_flow.py`: 64 pure LOC.
- `packages/agents/sub_agents/content_creator/prompt_contract.py`: 88 pure LOC.
- `packages/agents/sub_agents/content_creator/nodes.py`: 219 pure LOC.
- `packages/renderer/__tests__/rich-agent-fixtures.ts`: 120 pure LOC.
- `packages/renderer/__tests__/agent-renderer-rich-fixtures.test.ts`: 33 pure LOC.

## Notes
- One combined Python verification run failed when launched in parallel with renderer subprocess tests; direct renderer adapter probing and the same Python suite run serially passed. Treat this as a test-runner/resource-concurrency caveat, not a product behavior failure.
- Pre-existing sanitizer warning remains from allowing `<style>` tags in sanitize-html configuration.
- Post-implementation review initially found E2E type-safety and answer-marker brittleness blockers. Fixed by removing recursive test JSON aliases, guarding/casting rendered snapshot access, and removing the brittle Vietnamese answer marker from generic leakage deny-lists so legitimate roleplay labels do not cause false positives.
- A legacy content-creator test file still imported the moved private retry helper from `nodes.py`; preserved that compatibility by exposing alias names in `nodes.py`, then reran the expanded 73-test Python slice successfully.
