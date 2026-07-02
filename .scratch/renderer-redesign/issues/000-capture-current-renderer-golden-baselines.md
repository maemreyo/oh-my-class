---
title: Capture current renderer golden baselines before rewrite
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Capture golden baselines from the current renderer before any rewrite work changes rendering behavior. This is the safety net for the big-bang outcome: the new plugin registry can be built in slices, but each migrated artifact kind must be compared against known current output instead of being rewritten blind.

The baselines should cover representative current outputs for regular artifacts, Artifact UI paths, subprocess rendering, and exporter-driven rendering where applicable.

## Acceptance criteria

- [ ] Golden baseline harness renders representative current artifacts without using the new plugin registry.
- [ ] Baselines cover at least quiz, worksheet, drill, recap, infographic, lesson, answer_key, semantic-anchor vocabulary projections, inverse-thinking, root-cause session, and video-route where current renderers exist.
- [ ] Baselines include HTML snapshots and, for visual artifacts, screenshot or DOM-stable visual fixtures suitable for later comparison.
- [ ] Baseline capture records renderer/template/theme versions or source commit identity so future comparisons are meaningful.
- [ ] Documentation explains how migrated plugins compare against the baseline and how intentional visual changes are approved.
- [ ] The baseline harness is CI-runnable or clearly marked with an environment gate if browser screenshots are required.

## Blocked by

None - can start immediately
