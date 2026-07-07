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

## Amendment (2026-07-07 — design interview decisions)

- [ ] `STUDENT` is never added to the `Role` enum and no `users` row is created for a student — role tokens are minted via the existing `jwt_handler.py` signing path with a `role=STUDENT` claim scoped to `session_id`/`room_code` and a short expiry, with no persistent identity to revoke or leak.
- [ ] Join affordance is QR-code-primary (teacher projects, student scans, zero typing) with a 6-digit numeric code as the fallback for devices without a camera.
- [ ] Both join paths are rate-limited (IP + room code), reusing `services/gateway/routers/webhooks.py`'s sliding-window pattern, and the room code's validity is bounded to the session's lifetime.
- [ ] A CSV roster import (name + optional student ID, scoped to `class_id`) is supported so `identifiable`-tier sessions (TSP-01) can offer a name-select dropdown at join instead of free-text name entry — no integration with external SIS platforms in this slice.

## Blocked by

- TSP-01-session-lifecycle-privacy-retention.md
