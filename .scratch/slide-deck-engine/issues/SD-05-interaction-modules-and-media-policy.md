---
title: Add registered slide interactions and two-tier media policy
status: ready-for-agent
labels: [slide-deck-engine, interactions, media, ready-for-agent]
created: 2026-07-06
---

## Parent

ADR-041 and ADR-042.

## What to build

Add production interaction and media modules for `slide_deck` using registries, not ad hoc template branches. Interactions should be offline-first and non-persistent in v1, with no backend writes or student analytics. Media should support rich classroom use while preserving offline standalone exports by default.

The initial interaction set should include at least reveal/progression, quick check, poll prompt, timer, discussion prompt, exit ticket, and think-pair-share. Each module must declare schema, render behavior, print behavior, no-JS fallback, accessibility requirements, and answer/teacher-only policy.

Media policy should distinguish default offline packaged media from optional online embeds. Online media must be explicitly flagged, teacher-visible, and paired with fallback content.

## Acceptance criteria

- [ ] `SlideInteractionRegistry` contains registered modules for reveal, quick check, poll prompt, timer, discussion prompt, exit ticket, and think-pair-share.
- [ ] Each interaction has schema validation, renderer support, print/no-JS fallback, accessibility metadata, and tests.
- [ ] Quick check supports teacher-only answer guidance without putting correct answers into student-facing DOM.
- [ ] Media blocks validate alt text, media kind, source policy, and fallback requirements.
- [ ] Offline export rejects unmanaged external URLs and supports inline SVG/data URI/local packaged assets according to policy.
- [ ] Optional online media carries `requires_network` metadata, teacher preview warning, and fallback instructions.

## Blocked by

- SD-04 slide surfaces and answer-leak-safe projection.

## References

- `docs/adr/041-slide-deck-registries-and-interaction-modules.md`
- `docs/adr/042-slide-deck-surfaces-quality-and-release-gates.md`
- `common/contracts/components/registry.py`
- `packages/renderer/src/inline-assets.ts`
- `packages/quality/compliance_policy.py`

## Implementation notes

- Do not persist student responses in this issue.
- Do not introduce external script/framework dependencies.
- Keep complex drag/drop or scored classroom response collection deferred unless it can meet the same registry/test/fallback bar.
