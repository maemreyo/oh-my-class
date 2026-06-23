# ADR-001: Reverse Proxy Strategy

## Status

**Decided** (2026-06-23) — Dev: skip. Prod: decide Nginx vs Caddy before deploy.

## Context

The oh-my-class architecture has two frontend services:
- Gateway (FastAPI) on port 8001
- Dashboard (Next.js) on port 3000

Doc 01 (DeerFlow) uses Nginx as a single entry point to avoid CORS issues. The current scaffold has no reverse proxy — CORS middleware is configured in FastAPI, and Next.js handles rewrites.

## Decision

### Development (now)
**Skip Nginx/Caddy.** Use FastAPI CORS middleware + Next.js `next.config` rewrites. This is sufficient for local development and avoids adding complexity before it's needed.

### Production (before deploy)
**Choose between Nginx and Caddy** based on:
- SSL/TLS requirements
- Rate limiting needs
- Static asset serving
- Team familiarity

**Decision deadline**: Before first production deployment. Not during deploy.

## Consequences

- **Dev**: Simpler setup, one fewer container. CORS + rewrites handle cross-origin.
- **Prod**: Must decide before deploy. Adding a reverse proxy later requires updating docker-compose and gateway/web configs.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **Nginx** | Battle-tested, fine-grained control, widely documented | Complex config, manual SSL |
| **Caddy** | Auto-HTTPS, simpler config, less boilerplate | Less mature, fewer examples |
| **No proxy (prod)** | Simplest | No SSL termination, no rate limiting, CORS still needed |
