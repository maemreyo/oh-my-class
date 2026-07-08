# ADR-050: unit_planner / sequence_critic Remain Deterministic, Deferred to td-006/td-021

## Status

**Accepted** (2026-07-08) — produced from the `.scratch/design-reflection-2026-07-08.md` grill session. Formalizes an already-known gap: `.scratch/ROADMAP.md`'s 2026-07-01 audit already tags this as `td-006`/`td-021` ("deterministic Python, not the specced LLM agents").

## Context

`packages/agents/sub_agents/unit_planner/nodes.py` imports no LLM at all. `_build_sequence` generates a `LessonSequence` (session count, Bloom-level progression, knowledge components) entirely from `ClassProfile` heuristics (`_session_count`, `_bloom_levels`, `_methodology_for`) and placeholder text (`title=f"{topic}: session {order_index}"`, `description=f"Core knowledge component {index} for {topic}"`).

Separately from the "is this deterministic-by-design or stale" question, the generated `LessonSequence.rationale` field is factually wrong: it hard-codes `"retrieve grounding → Curricular-CoT adapt → validate; deterministic seam for unit planning."` — describing an LLM chain-of-thought adaptation step that does not exist in this code path. This is a correctness bug independent of the architecture question (a caller trusting `rationale` as a description of what happened is misled), and is fixed immediately regardless of this ADR's outcome.

The larger question — whether `unit_planner`/`sequence_critic` should gain real LLM reasoning — is already tracked as roadmap technical debt (`td-006`, `td-021`) predating this session. This ADR does not re-litigate that scope; it records that the current state is intentional-for-now (not an oversight) and points to the existing tracked debt for the eventual real implementation.

## Decision

1. **`unit_planner`/`sequence_critic` remain deterministic** for the current product phase. The `td-006`/`td-021` backlog items in `.scratch/ROADMAP.md` remain the authoritative tracking for eventually adding real LLM reasoning here — this ADR does not change their priority.
2. **`rationale`'s misleading text is corrected now**, independent of and not blocked on td-006/td-021, to accurately describe the current deterministic seam (e.g. `"deterministic template seam; no LLM reasoning step"`). See `.scratch/llm-integration-completion/LIC-05-unit-planner-rationale-fix.md`.
3. Placeholder knowledge-component titles/descriptions (`f"Core knowledge component {index} for {topic}"`) are left as-is under this ADR; they are in scope for td-006/td-021's eventual real implementation, not a standalone fix.

## Consequences

- Nobody reading `LessonSequence.rationale` in logs, debugging output, or a future audit is misled into thinking a chain-of-thought LLM step already ran here.
- The architecture decision itself stays consolidated in `td-006`/`td-021` — this ADR does not fork a second, competing backlog entry for the same eventual work.
