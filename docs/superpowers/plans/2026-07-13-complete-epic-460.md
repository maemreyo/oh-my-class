# Complete EPIC 460 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining Teaching Content Factory V2 work with reproducible architecture, quality, effectiveness, performance, and final release evidence.

**Architecture:** Keep evaluation, effectiveness analytics, and load-SLO math in package-neutral contracts. Put HTTP driving and release orchestration in scripts. Make every release artifact deterministic, hash-addressed, signed when a key is supplied, and fail closed when live evidence is absent.

**Tech Stack:** Python 3.12, Pydantic contracts already in the repository, pytest, FastAPI/PostgreSQL worker integration, Docker Compose, GitHub CLI.

## Global Constraints

- Do not close an issue using synthetic-only or mock-only evidence.
- Preserve exact ArtifactDocument/AnswerSet/item version lineage.
- No student PII in benchmark, analytics, cache, prompt, or report payloads.
- Critical answer, privacy, factual, curriculum, accessibility, or safety failures cannot be hidden by an aggregate score.
- #474 and #460 close only after every declared blocker is closed and the release profile is green.

---

### Task 1: Repair architecture truth

**Files:**
- Regenerate: `docs/system/architecture.manifest.json`
- Refresh: `docs/anatomy/_manifest.json`
- Repair only verified references in: `docs/anatomy/*.md`

- [ ] Reproduce the three architecture failures.
- [ ] Regenerate the architecture manifest from `scripts/generate_architecture_manifest.py`.
- [ ] Repair the single broken anatomy reference by resolving the cited source symbol/path.
- [ ] Recompute anatomy module hashes with the repository's own `state.hash_module` implementation.
- [ ] Run `make check-architecture` and commit.

### Task 2: Deliver #130 load/SLO harness

**Files:**
- Create: `common/contracts/performance/load_harness.py`
- Create: `common/contracts/tests/performance/test_load_harness.py`
- Create: `scripts/run_content_factory_load_test.py`
- Modify: `Makefile`

- [ ] Write failing percentile, SLO, queue-drain, red-control, and baseline-regression tests.
- [ ] Implement deterministic report math and fail-closed SLO evaluation.
- [ ] Implement a real HTTP driver for `/teaching-packs/runs` and `/teaching-packs/runs/{run_id}`.
- [ ] Add smoke and release commands; release requires a live base URL and auth token.
- [ ] Run green and deliberately red evidence profiles and commit.

### Task 3: Complete #470 benchmark release gate

**Files:**
- Create: `common/contracts/content_evaluation/release_gate.py`
- Create: `common/contracts/tests/content_evaluation/test_release_gate.py`
- Modify: `scripts/run_content_benchmark.py`
- Modify: `Makefile`

- [ ] Write failing pairwise-coverage, mutation, calibration, signature, and regression tests.
- [ ] Implement deterministic covering-array generation across all declared axes.
- [ ] Implement mutation controls for hallucination, ambiguity, answer leakage, shallow pedagogy, bias, unsafe context, and fake citations.
- [ ] Implement blind teacher-label calibration, inter-rater agreement, false-pass analysis, signatures, and baseline comparison.
- [ ] Emit machine-readable and human-readable release reports; commit after the release gate is green.

### Task 4: Complete #473 governed effectiveness loop

**Files:**
- Create: `common/contracts/effectiveness/governance.py`
- Create: `common/contracts/tests/effectiveness/test_governance.py`
- Create: `services/gateway/effectiveness_ingestion.py`
- Create: `services/gateway/tests/test_effectiveness_ingestion.py`
- Modify: `scripts/run_effectiveness_simulation.py`
- Modify: `Makefile`

- [ ] Write failing opt-out, deletion, tenant isolation, lineage split, tiny-cohort, discrimination, reliability, ambiguity, and policy-boundary tests.
- [ ] Implement an append-only privacy ledger and exact-version aggregation.
- [ ] Implement live/export ingestion that pseudonymizes actors before persistence.
- [ ] Emit uncertainty/deletion/lineage reports and prove proposals never auto-apply.
- [ ] Run the published synthetic classroom simulation and commit.

### Task 5: Certify #474 and close #460

**Files:**
- Create: `scripts/certify_content_factory_v2.py`
- Create: `tests/test_content_factory_certification.py`
- Modify: `Makefile`
- Modify: `docs/testbook/runbook.md`

- [ ] Write failing tests for required certification steps, blocker enforcement, evidence hashing, signing, and rollback record.
- [ ] Implement `make certify-content-factory-v2` over architecture, content intelligence, specialist, V2, runtime, benchmark, effectiveness, load, schema, and integration gates.
- [ ] Run the release profile against PostgreSQL, external worker, object storage, API, renderer/export/editor/session tests, and real load endpoint.
- [ ] Emit signed JSON manifest, human report, environment versions, and rollback record.
- [ ] Close #130, #470, #473, #474, then #460 only after fresh green evidence and push the commits.
