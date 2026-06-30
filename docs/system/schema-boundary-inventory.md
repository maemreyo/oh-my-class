# Schema boundary inventory

Every model below crosses a backend/frontend, API, event, or runtime package seam.
Each module must stay registered in `scripts/schema_codegen_config.py::MODELS`, so
`scripts/generate_zod_schemas.py` emits a Zod schema and
`scripts/verify_schema_parity.py` checks drift from the Pydantic source.

| Contract module | Boundary surface | Codegen status |
| --- | --- | --- |
| `common.contracts.artifact` | agent output → renderer/gateway quality | registered |
| `common.contracts.artifact_workflow` | artifact workflow persistence/runtime handoff | registered |
| `common.contracts.errors` | gateway HTTP error envelopes → frontend | registered |
| `common.contracts.inverse_thinking` | methodology payloads embedded in lesson plans and renderer projections | registered |
| `common.contracts.judge_output` | quality judge output → gateway/runtime | registered |
| `common.contracts.lesson_plan` | planner output → teacher-visible plan and renderer | registered |
| `common.contracts.lesson_sequence` | ADR-017 unit planning sequence → unit APIs | registered |
| `common.contracts.quality` | quality/healing reports → gateway/runtime surfaces | registered |
| `common.contracts.research_brief` | pre-planning search and artifact research guidance | registered |
| `common.contracts.run_contract` | run contract confirmation, persistence, resume flow | registered |
| `common.contracts.unit_view` | ADR-017 unit view and SSE payloads → frontend | registered |

Router-local DTOs in `services/gateway/routers/*_schemas.py` remain explicit
exceptions while they are only FastAPI transport wrappers verified by
`scripts/verify_frontend_api_contracts.py`. If one becomes a shared domain
contract or is imported outside the gateway router layer, move it to
`common/contracts` and register it here.
