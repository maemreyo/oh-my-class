---
title: Systemic schema-parity coverage for cross-boundary types
status: done
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Eliminate BE↔FE type drift across the whole surface. Domain contracts are codegen'd Pydantic→Zod, but several transport/event/view DTOs are hand-written TypeScript (a drift risk; addressed for units in topic-decomposition issue 001, but not system-wide).

- **Inventory** every type that crosses the BE↔FE boundary (API request/response, SSE event payloads, view models). Bring each under the `scripts/generate_zod_schemas.py` `MODELS` codegen registry, or explicitly document a justified exception.
- **CI guard**: extend `verify_schema_parity` + `verify_frontend_api_contracts` to fail the build on drift for all registered models, triggered on contract changes.
- **Enforcement**: a test that scans `common/contracts` for models referenced by API/event surfaces and asserts each is registered in the codegen registry — new boundary types must be registered, not hand-written.

## Acceptance criteria

- [x] An inventory exists; every cross-boundary type is either codegen-registered or has a documented exception.
- [x] `verify_schema_parity` + `verify_frontend_api_contracts` fail the build on any registered-model drift and run on contract changes.
- [x] A test asserts that boundary-referenced `common/contracts` models are present in the codegen `MODELS` registry.
- [x] Hand-written transport/event DTOs are migrated to generated types or explicitly justified.

## Detailed test suite

- [x] `common/schemas` parity: every registered model's generated Zod matches its Pydantic JSON schema (names + required/optional).
- [x] `scripts/verify_frontend_api_contracts.py` passes for all API endpoints, including units.
- [x] `tests/test_boundary_types_registered.py`: a model used in an API/event surface but missing from the codegen registry fails the test.
- [x] Drift sentinel: an intentional field rename in a Pydantic contract without regen fails parity.
- [x] Run `make check-schemas` (or `generate:schemas` + `verify:schemas` + `verify:frontend-api`).

## Blocked by

None - can start immediately
