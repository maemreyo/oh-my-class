# ADR-008: Artifact Workflow and Rendered Snapshots

## Status

**Decided** (2026-06-27) — Pipeline V2 generates, validates, renders, and approves artifacts individually with persisted rendered snapshots.

## Context

The current Content Creator attempts to generate an entire pack in one JSON response. Live Math and English runs showed this is fragile: large outputs timeout or produce malformed/empty JSON, and retries regenerate the entire pack. The current approval UI also shows raw JSON, but the product promise is standalone print-and-use HTML.

## Decision

Pipeline V2 uses artifact-level generation and workflow state.

Initial supported artifact types:

- `lesson`
- `worksheet`
- `quiz`
- `recap`

Initial supported export:

- standalone `html`

Other artifact and export types are deferred behind extension seams.

State model:

- `artifacts[]` remains the clean final output view.
- `artifact_workflow` stores internal execution state per artifact:
  - status;
  - attempts;
  - contract revision id;
  - research guidance id;
  - validation status;
  - judge score;
  - healing attempts;
  - snapshot refs;
  - last error.

Generation model:

- one artifact per generation call;
- bounded parallelism with explicit dependencies;
- retry/heal only affected artifacts;
- section-level splitting only when an artifact is too large.

Rendering model:

- render before teacher content approval;
- validate standalone HTML before approval;
- teacher approves rendered preview, not JSON;
- technical JSON/details remain optional.

Snapshot model:

- rendered HTML snapshots are persisted by content/hash;
- state stores references, not giant HTML blobs;
- approved export packages the exact approved snapshot.

Snapshot metadata includes:

- artifact id/type;
- content hash;
- HTML hash;
- renderer version;
- template version;
- theme version;
- standalone validity;
- creation and approval timestamps.

## Consequences

- One broken artifact no longer destroys a whole pack.
- UI can show artifact-level progress and quality status.
- Teacher approval matches what students will see.
- Approved outputs are reproducible even if templates later change.
- Core V2 scope is deep and production-ready instead of broad and shallow.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Keep pack-level generation | Simple graph | Fragile, slow retries, poor progress UX |
| Split by section immediately | Smallest units | Harder coherence and more orchestration complexity |
| Artifact-level generation | Natural seam and scalable | Requires artifact workflow state |
| Render only at export | Simpler approval | Teacher approves the wrong representation |
