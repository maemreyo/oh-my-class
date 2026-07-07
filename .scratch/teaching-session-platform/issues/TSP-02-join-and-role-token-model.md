---
title: Anonymous-first join and scoped session role tokens
status: ready-for-agent
labels: [ready-for-agent, teaching-session, security]
created: 2026-07-07
---

## Parent

ADR-046: TeachingSession Platform for Slide Deck Delivery

## What to build

Design the join and permission model for future live slide-deck sessions. Student join should be anonymous-first with a room code and optional alias/seat/group. Teacher auth owns the session and mints scoped role tokens for controller, display, student, and observer surfaces.

This slice should prevent broad account privileges from leaking into classroom roles and should make teacher-only data inaccessible to student/display tokens.

## Acceptance criteria

- [ ] Join modes are specified: anonymous, pseudonymous, and authenticated roster.
- [ ] Role model is specified: controller, display, student, observer; co-teacher is deferred.
- [ ] Teacher ownership/auth is required to mint controller tokens.
- [ ] Role tokens are scoped to session, role, expiry, and policy.
- [ ] Student/display/observer tokens cannot access teacher-only exports, answer keys, controller actions, or retention settings outside their role.
- [ ] Anonymous-first join does not require student email by default.
- [ ] Evidence and analytics can label identity mode without storing unnecessary PII.

## Blocked by

- TSP-01-session-lifecycle-privacy-retention.md
