# System Diagram: oh-my-class

## System context

```mermaid
graph LR
    teacher((Teacher)) --> web[Web Dashboard]
    teacher --> session((Live Session))
    web --> gateway[Gateway :8001]
    session --> gateway
    gateway --> agents[Agents Pipeline]
    agents --> llm[9Router :20228]
    agents --> search[Web Search]
    gateway --> db[(PostgreSQL)]
    gateway --> redis[(Redis)]
    gateway --> langfuse[Langfuse]
    langfuse --> clickhouse[(ClickHouse)]
    langfuse --> minio[(MinIO)]
```

## Module dependency graph

```mermaid
graph TD
    web[web<br/>Next.js] --> schemas[schemas<br/>Zod Types]
    web --> renderer[renderer<br/>Eta Templates]
    exporters[exporters<br/>GIFT/H5P/Anki] --> renderer
    exporters --> schemas
    agents[agents<br/>LangGraph] --> contracts[contracts<br/>Pydantic]
    agents --> quality[quality<br/>6-Layer Gates]
    agents --> renderer
    agents --> methodologies[methodologies<br/>Inverse Thinking]
    quality --> contracts
    methodologies --> contracts
    schemas --> contracts
    gateway[gateway<br/>FastAPI] --> agents
    gateway --> contracts
    gateway --> quality
    agents --> gateway
    renderer --> schemas
    llm_client[llm-client<br/>LLM Wrapper] --> agents
    notifications[notifications<br/>Fan-out] -.-> gateway
    infra[infra<br/>Docker Compose]
    tests[tests<br/>E2E/Unit]
    tests --> agents
    tests --> gateway
    tests --> contracts
```

Modules: [agents](modules/agents.md) · [quality](modules/quality.md) · [renderer](modules/renderer.md) · [exporters](modules/exporters.md) · [gateway](modules/gateway.md) · [web](modules/web.md) · [contracts](modules/contracts.md) · [schemas](modules/schemas.md) · [llm-client](modules/llm-client.md) · [notifications](modules/notifications.md) · [methodologies](modules/methodologies.md) · [infra](modules/infra.md)

## Key flows

### Teaching Pack Generation

```mermaid
sequenceDiagram
    participant T as Teacher
    participant W as web
    participant G as gateway
    participant A as agents
    participant Q as quality
    participant R as renderer

    T->>W: Create pack request
    W->>G: POST /teaching-packs/runs
    G->>G: Create Run + RunJob in DB
    G-->>W: 202 Accepted
    G->>G: Worker picks up job
    G->>A: graph.ainvoke(initial_state)
    A->>A: setup_contract → triage
    A->>A: preplanning_search → planning_blueprint
    A->>A: post_blueprint_research → artifact_workflow
    A->>A: generate_one_artifact (parallel via Send)
    A->>R: renderArtifact(artifact)
    R-->>A: standalone HTML
    A->>Q: quality_issues() + AdaptiveJudge
    Q-->>A: pass/fail
    alt quality failed
        A->>A: heal → retry/rewrite/reroute
    end
    A->>Q: compliance_gate_state()
    Q-->>A: hard-block check
    A->>G: interrupt() → HITL gate
    G->>W: SSE: content_approval gate
    T->>W: Approve
    W->>G: POST /resume
    G->>A: graph.ainvoke(Command(resume=...))
    A->>R: build_snapshot()
    R-->>A: rendered snapshots
    A->>A: export_finalize
    G->>W: SSE: run completed
```

Modules involved: [gateway](modules/gateway.md), [agents](modules/agents.md), [quality](modules/quality.md), [renderer](modules/renderer.md)

### Unit Planning (Multi-Session)

```mermaid
sequenceDiagram
    participant T as Teacher
    participant G as gateway
    participant A as agents
    participant U as unit_planner

    T->>G: POST /teaching-packs/runs (mode=plan_unit)
    G->>A: graph.ainvoke(initial_state)
    A->>A: triage → route to plan_unit path
    A->>U: planner + sequence_critic
    U-->>A: LessonSequence
    A->>G: interrupt() → unit_approval
    G->>T: SSE: unit_approval gate
    T->>G: Approve
    G->>A: resume
    A->>A: unit_prep → END
```

Modules involved: [agents](modules/agents.md), [gateway](modules/gateway.md)

### Live Teaching Session

```mermaid
sequenceDiagram
    participant S as Student
    participant T as Teacher
    participant G as gateway
    participant R as Redis
    participant DB as PostgreSQL

    T->>G: POST slide advance
    G->>DB: Write TeachingSessionEvent
    G->>R: Pub/Sub broadcast
    R-->>S: SSE: slide_changed
    S->>G: POST submit_response
    G->>DB: Write event + aggregate
    G->>R: Pub/Sub broadcast
    R-->>T: SSE: aggregate_updated
```

Modules involved: [gateway](modules/gateway.md)
