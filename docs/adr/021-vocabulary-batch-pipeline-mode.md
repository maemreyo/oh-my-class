# ADR-021: Vocabulary Batch Pipeline Mode

## Status

**Decided** (2026-07-01) — Vocabulary batch generation will be a specialized `vocabulary_batch` mode inside the authoritative teaching-pack runtime, not a separate sidecar application and not a new top-level artifact type.

## Context

Teachers need to paste many confusing English word clusters and receive production-ready teaching outputs for each cluster. A cluster may contain two terms or many terms:

```text
travel / journey / trip / voyage / excursion
fare / ticket / fee
historic / historical / classic / classical
```

The expected output is not a generic lesson pack. For each cluster, the system should generate:

- a standalone teaching HTML for the teacher,
- a standalone teaching HTML for students,
- lightweight practice for recall and discrimination,
- optional LMS exports for the practice surface,
- per-cluster status, evidence, and review controls.

Existing architecture already has the pieces this mode should reuse: the teaching-pack graph, run/job persistence, HITL gates, BaseStore memory, renderer/exporter boundaries, methodology registry, quality gates, and event/status surfaces. Creating a separate vocabulary tool would duplicate these capabilities and make later integration with packs, memory, and exports harder.

The grilling session resolved several constraints:

1. User input is free-form teacher text, not a required Markdown/YAML schema.
2. A cluster is the pedagogical unit; it is not itself an artifact.
3. The system should target medium batches of 20–100 clusters per run.
4. Teacher and student outputs must be separate files so teacher-only notes and answer keys never leak into student HTML.
5. `needs_review` must be a first-class state, not an exception or silent pass.
6. Existing agents should be reusable capabilities with profile-specific contracts, not feature-specific one-off agents.

## Decision

### 1. Add `vocabulary_batch` as a Teaching Pack pipeline mode

`vocabulary_batch` extends the teaching-pack runtime as a mode. The user-facing UI may present a dedicated Vocabulary Batch Generator, but the backend remains the teaching-pack platform: runs, jobs, gates, events, snapshots, quality, and export infrastructure are reused.

The mode has a specialized orchestration path:

```text
setup_contract
  → normalize_vocab_batch_input
  → lexical_grounding
  → semantic_anchor_synthesis
  → practice_generation
  → vocabulary_batch_quality
  → teacher_review
  → export_finalize
```

This is a mode-specific stage sequence, not a fork of the runtime. Existing single-pack modes must remain zero-regression.

### 2. Model clusters as child workflow units, not artifacts

A `VocabularyClusterWorkflow` is the child unit of a vocabulary batch run. It owns per-cluster status, evidence, retry history, review state, and export references. The artifacts are derived from that cluster workflow:

```text
VocabularyClusterWorkflow
  normalized_input
  lexical_grounding
  semantic_anchor_cluster
  practice_set
  quality_result
  teacher_edits
  export_refs
```

This avoids overloading `artifact_type` with a pedagogical unit. HTML and LMS files are outputs of the cluster; the cluster itself remains domain state.

### 3. Use reusable agent capabilities with stage-specific contracts

The mode reuses existing capability roles instead of creating bespoke feature agents:

| Stage | Capability | Profile / contract |
|---|---|---|
| Input normalization | Normalizer capability | free-form cluster extraction + ambiguity report |
| Lexical grounding | Researcher capability | dictionary-grounded lexical distinction bundle |
| Semantic synthesis | Content synthesis / content creator capability | `SemanticAnchorCluster` RCM data |
| Practice generation | PracticeGenerator capability | `PracticeSet` with recall/discrimination items |
| Review | Reviewer / quality gate capability | lexical pedagogy, projection safety, standalone invariants |

`PracticeGenerator` is a reusable capability separated from `ContentCreator`. Teaching content and assessment practice have different contracts, leakage risks, exports, and quality checks.

### 4. Normalize free-form input into a structured ambiguity report

Teachers may paste loose text. The InputNormalizer produces a structured report:

```text
ready_clusters
ambiguous_clusters
clarifying_questions
skipped_spans
parse_confidence
```

The agent does not directly interrupt the teacher. It returns a structured ambiguity report; the gateway/UI decides whether to continue, ask, skip, or confirm. High-confidence clusters can continue automatically. Low-confidence clusters do not block the entire batch.

### 5. Ground lexical distinctions lightly, then cache reviewed knowledge

Lexical grounding uses the Researcher capability with trusted dictionary/reference sources. Student-facing copy stays memorable and simple; teacher-facing notes preserve source notes, nuance warnings, and uncertainty.

The system stores knowledge in two layers:

- cluster snapshots, for audit and re-rendering;
- reusable term-distinction records, for future clusters with overlapping terms.

Teacher corrections are saved as per-teacher or per-tenant preferences by default. They are promoted to shared lexical knowledge only after explicit review.

### 6. Use fixed configurable concurrency first

The mode is designed for medium batches, so processing is asynchronous and per-cluster. Initial production concurrency is fixed and configurable by stage:

```text
lexical_grounding: low concurrency
semantic_synthesis: medium concurrency
practice_generation: medium concurrency
render/export: higher concurrency
```

The interfaces must allow later adaptive concurrency based on provider health, budget, queue load, and cluster complexity.

### 7. Use typed failure strategy and per-cluster evidence ledger

Failures are classified by layer:

- input parse low confidence → ambiguity report;
- insufficient lexical sources → `needs_review`;
- lexical contradiction → `needs_review` or `failed` by severity;
- schema invalid → regenerate the structured output;
- projection leakage → hard fail;
- external asset in HTML → hard fail;
- unsupported LMS export → skip that export with reason.

Every cluster records an evidence ledger containing normalized input, grounding sources, generated contracts, quality results, teacher edits, approval state, export refs, and retry history. The ledger stores structured evidence and rationale fields, not chain-of-thought.

### 8. Export by cluster status

The status model is three-valued:

| Status | Export behavior |
|---|---|
| `passed` | teacher + student teaching HTML, teacher + student practice HTML, optional GIFT/H5P practice exports |
| `needs_review` | teacher review files only; student/practice/LMS exports withheld until teacher approval |
| `failed` | diagnostic report only |

The batch ZIP includes an offline `index.html` plus a manifest. The index links cluster outputs and surfaces warnings for `needs_review` or failed clusters.

## Consequences

- Vocabulary batch becomes a first-class production flow without duplicating the teaching-pack control plane.
- Per-cluster workflow state enables partial success, retry, review, pagination, and selected export.
- Existing agents remain reusable capabilities; vocabulary-specific behavior lives in stage contracts and profiles.
- The runtime gains new mode-specific stages and persistence requirements, so tests must cover topology, failure isolation, progress UX, and export policy.
- Student-safe output is protected by projection separation and status-aware export rules.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Build a separate Vocabulary Batch app | Clean initial UX | Duplicates jobs, gates, snapshots, quality, exports, memory, and observability |
| Force vocabulary batch through ordinary `generate_pack` | Minimal mode surface | Planning flow does not match batch/cluster semantics; weak per-cluster review and retry |
| Add a new artifact type for semantic clusters | Simple renderer dispatch | Misrepresents clusters as artifacts; harder to manage practice, evidence, and status |
| Let ContentCreator handle everything | Fewer capabilities | Bloated prompt, weak SoC, harder testing, higher leakage risk |
| One HTML file with teacher/student toggle | Convenient preview | Teacher-only data remains in the student file DOM; violates separation intent |
| Fail entire batch on one uncertain cluster | Simple status semantics | Bad UX for 20–100 cluster batches; loses partial value |
