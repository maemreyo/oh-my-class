# oh-my-class

> AI-powered teaching pack generator for K-12 education.
> A teacher describes a lesson → the system produces a complete, print-and-use HTML teaching pack.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Teacher (Browser)                         │
│              Next.js 15 Dashboard :3000                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST / WebSocket (SSE)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               FastAPI Gateway  :8001                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         LangGraph Runtime (Embedded)                 │    │
│  │       12-step pipeline with 2 teacher gates          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  LiteLLM Proxy :4000 ──► 9Router Sidecar :20128            │
│  PostgreSQL :5432 │ Redis :6379                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

- **100% 9Router**: All LLM traffic routes through 9Router sidecar. NO paid fallbacks. Budget cap = $0 for any direct provider.
- **Fail safely**: When 9Router is unreachable → queue run (LangGraph checkpointer persists state) or return clear error to teacher. Never silently charge money.
- **Standalone HTML**: All output is self-contained — no CDN, no external assets, works offline.

## Folder Structure

```
oh-my-class/
├── packages/                    # Reusable libs — never import from apps/ or services/
│   ├── agents/                  # LangGraph multi-agent pipeline (Python)
│   ├── quality/                 # 6-layer quality gate system (Python)
│   ├── renderer/                # Eta template engine → standalone HTML (TypeScript)
│   └── exporters/               # Export format generators (TypeScript)
├── common/                      # Shared — lowest layer, no upward imports
│   ├── branding/kits/           # Theme definitions (default, ocean, forest)
│   ├── schemas/                 # TypeScript types + Zod schemas
│   └── contracts/               # Pydantic models (Python)
├── services/                    # Runtime services — import from packages/
│   ├── gateway/                 # FastAPI + embedded agent runtime :8001
│   ├── proxy/                   # LiteLLM proxy :4000
│   └── router/                  # 9Router sidecar :20128
├── apps/                        # Application layer — import from packages/ and common/
│   └── web/                     # Next.js 15 teacher dashboard :3000
├── skills/                      # Markdown skills injected into agent prompts
├── infra/                       # Docker + compose configs
├── scripts/                     # Utility scripts
├── tests/                       # Cross-package integration + E2E tests
└── docs/                        # Reports and documentation
```

### Import Rules (enforced by CI)

| Layer | Can Import From | Cannot Import From |
|-------|----------------|-------------------|
| `common/` | (nothing above) | packages/, services/, apps/ |
| `packages/` | common/ | services/, apps/ |
| `services/` | packages/, common/ | apps/ |
| `apps/` | packages/, common/, services/ | — |

Enforced by:
- **Python**: `import-linter` (`.importlinter` in pyproject.toml)
- **TypeScript**: `dependency-cruiser` (`.dependency-cruiser.cjs`)

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 22+
- pnpm
- Docker + Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python workspace manager)

### Setup

```bash
# Clone and bootstrap
git clone <repo-url> oh-my-class
cd oh-my-class

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys (see .env.example for required vars)

# Run setup script
bash scripts/setup.sh

# Or manual setup:
uv sync                          # Python workspace
pnpm install                     # TypeScript workspace
python scripts/generate_theme.py # Generate theme CSS
docker compose -f infra/compose/docker-compose.yml up -d
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| Gateway | 8001 | FastAPI REST API + WebSocket |
| Dashboard | 3000 | Next.js teacher dashboard |
| LiteLLM | 4000 | LLM proxy (all traffic via 9Router) |
| 9Router | 20128 | LLM router (free-tier aggregation) |
| PostgreSQL | 5432 | Database (checkpoints, metadata) |
| Redis | 6379 | Cache (LiteLLM) + shared state |

### Running Tests

```bash
# Python
uv run pytest

# TypeScript
pnpm test

# Import boundary checks
lint-imports                      # Python
pnpm lint:deps                    # TypeScript (dependency-cruiser)
```

## 12-Step Pipeline

```
Step 01 · Preflight        Validate raw teacher input
Step 02 · Quickstart       Initialize run: create thread, dirs, metadata
Step 03 · Blueprint        Planner Agent → LessonPlan JSON
Step 04 · Teacher Gate 1   Teacher approves/edits/rejects blueprint
Step 05 · Pack Scope       Determine artifact types for this run
Step 06 · Visual Engine    Choose theme, layout per artifact
Step 07 · Research         Researcher Agent → ResearchBundle JSON
Step 08 · Generate         ContentCreator Agent → ArtifactContent[] JSON
Step 09 · Import           Assemble artifacts; run Layer 1–3 gates
Step 10 · Review           LLM-as-Judge (Layer 4); self-heal if needed
Step 11 · Teacher Gate 2   Teacher approves/edits/rejects content
Step 12 · Validate         Layer 6 multi-judge; schema + contract check
Step 13 · Export           Package to requested format(s)
```

## Skills

> **Note**: Only 4 of the 7 originally sketched skills (doc 03) are implemented for MVP.
> The following are intentionally deferred: `agent-orchestrator`, `validation-fixer`, `design-kit-importer`.
> The `engineering/` group (20 skills) is a separate concern — tracked in the engineering backlog.

| Skill | Purpose |
|-------|---------|
| `blueprint-designer` | UbD, Bloom's, Gagné's 9 Events — lesson planning |
| `pack-generator` | Template rules, no-CDN constraints — content generation |
| `artifact-reviewer` | G-Eval rubric, hard blocks — quality review |
| `export-assistant` | GIFT/H5P format specs — export |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | LangGraph 1.x |
| Backend | FastAPI (Python 3.12) |
| Frontend | Next.js 15 (TypeScript) |
| Template Engine | Eta (JS/TS) |
| LLM Gateway | LiteLLM Proxy → 9Router Sidecar |
| Cache | Redis 7 |
| Persistence | PostgreSQL 16 |
| Validation | Pydantic v2 + Zod v4 |
| Testing | pytest + Vitest |

## License

MIT