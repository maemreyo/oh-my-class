---
title: Slide deck display preference migration and backward compatibility
status: ready-for-agent
labels: [ready-for-agent, slide-deck]
created: 2026-07-07
---

## Parent

ADR-043: Slide Deck Display Preferences and Projection Boundaries

## What to build

Ensure existing slide-deck artifacts, snapshots, and exports continue to render safely after typed display preferences are introduced. Older `SlideDeckData` objects will not have display preference fields, so the system must resolve safe defaults at the projection/render/export boundary without treating old data as invalid generated content.

This slice should protect replayability and export reproducibility. Missing preferences must default to presentation-safe/student-safe behavior, not teacher mode or visible robotic chrome. Compatibility should be explicit and localized to boundary normalization rather than scattered defensive checks across templates.

## Acceptance criteria

- [ ] Existing slide-deck snapshots without display preferences render through preview/export using safe defaults.
- [ ] Missing or partial display preferences normalize to the ADR-043 defaults at a single clear boundary.
- [ ] Backward compatibility does not let old artifacts expose teacher notes, answer keys, or teacher-only interaction data to student/presentation surfaces.
- [ ] Export replay records effective preferences so future renders can reproduce the chosen surface/layout/chrome.
- [ ] Compatibility code is not implemented as loose ad-hoc checks inside every template branch.
- [ ] Technical guards cover legacy deck input, partial preferences, invalid values, and snapshot/export replay.
- [ ] Real-LLM acceptance in SDH-07 still runs on newly generated decks; this slice additionally proves old deck compatibility through existing real export artifacts where available.

## Blocked by

- SDH-01-display-preferences-and-surface-contract.md
