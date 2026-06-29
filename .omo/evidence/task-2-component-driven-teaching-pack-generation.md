# Evidence: task 2 - content creator prompt contract

## Outcome
- Extracted the ContentCreator artifact prompt contract into `packages/agents/sub_agents/content_creator/prompt_contract.py`.
- `packages/agents/sub_agents/content_creator/nodes.py` now calls `build_single_artifact_prompt` and `retry_single_artifact_prompt` from that focused module.

## Behavior locked
- Prompts require component-first `ArtifactContent` JSON.
- Prompts ban raw HTML, CSS, class names, CDN links, and answer-key leakage.
- Prompts include artifact-specific richness requirements for active artifact types.

## Verification
- `uv run pytest packages/agents/tests/sub_agents/test_content_creator_component_prompt.py packages/agents/tests/sub_agents/test_content_creator_prompt_size.py packages/agents/tests/sub_agents/test_content_creator_per_artifact.py -q` passed as part of the combined focused run.
- Combined focused run: `uv run pytest tests/e2e/test_teaching_pack_component_driven_flow.py packages/agents/tests/sub_agents/test_content_creator_component_prompt.py packages/agents/tests/sub_agents/test_content_creator_prompt_size.py packages/agents/tests/sub_agents/test_content_creator_per_artifact.py -q` -> `37 passed`.
