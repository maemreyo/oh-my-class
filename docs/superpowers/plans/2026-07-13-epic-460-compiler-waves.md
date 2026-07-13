# EPIC 460 Compiler Waves Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix answer-shape verification, verify and close the previous EPIC 460 batch, then deliver tested production-connected increments for #470, #473, and #489-#496 through one typed compiler path without falsely closing incomplete issues.

**Architecture:** Keep the existing Content Orchestrator and specialists. Add immutable deterministic compiler contracts and one runtime adapter; keep benchmark/effectiveness planes independent and non-authoritative.

**Tech Stack:** Python 3.13 project runtime, Python 3.9-compatible installer, Pydantic v2, pytest, Make, Git, GitHub CLI.

## Global Constraints

- Start from commit `e3198d44ed240596b01e24322a589617ea2f799b` or a descendant with identical guarded blobs.
- No raw request becomes downstream semantic authority.
- Hard constraints and critical quality lanes are non-compensatory.
- Student content remains structurally separated from answer derivations.
- Issue closure requires all verification commands and blocker checks in one run.

---

### Task 1: Correct constructed-response AnswerSet semantics

**Files:**
- Modify: `common/contracts/answer_set.py`
- Test: `common/contracts/tests/test_answer_set_constructed_response.py`

- [ ] Add a failing test reproducing `practice-worked_example-1` with a prose answer not present in option IDs.
- [ ] Run `uv run pytest common/contracts/tests/test_answer_set_constructed_response.py -q` and confirm the unknown-option failure.
- [ ] Derive `correct_option_ids` only when the answer is an option key; otherwise derive `accepted_answers`.
- [ ] Re-run the regression and `make check-specialist-registry`.

### Task 2: Add calibrated benchmark and effectiveness planes

**Files:**
- Create: `common/contracts/content_evaluation/benchmark.py`
- Create: `common/contracts/effectiveness/feedback.py`
- Create: `scripts/run_content_benchmark.py`
- Create: `scripts/run_effectiveness_simulation.py`
- Test: `common/contracts/tests/content_evaluation/test_benchmark.py`
- Test: `common/contracts/tests/effectiveness/test_effectiveness.py`

- [ ] Add negative controls for shallow objective restatement and critical failure override.
- [ ] Add exact-version aggregation, minimum cohort, opt-out, and proposal-only tests.
- [ ] Implement deterministic reports, calibration metrics, privacy-safe observations, and policy proposals.
- [ ] Run `make benchmark-content-smoke` and `make check-effectiveness-loop`.

### Task 3: Add canonical intent and objective reasoning

**Files:**
- Create: `common/contracts/pedagogical_compiler/intent.py`
- Create: `common/contracts/pedagogical_compiler/objective_graph.py`
- Test: `common/contracts/tests/pedagogical_compiler/test_compiler_kernel.py`

- [ ] Test deterministic intent hashing, punctuation invariance, material clarification, atomic objective decomposition, stable KC identity, evidence claims, and acyclicity.
- [ ] Implement immutable contracts and deterministic builders.
- [ ] Run `make check-teaching-intent check-objective-graph`.

### Task 4: Add Program IR and Semantic IR

**Files:**
- Create: `common/contracts/pedagogical_compiler/program_ir.py`
- Create: `common/contracts/pedagogical_compiler/semantic_ir.py`

- [ ] Test exact time budgets, objective/evidence coverage, semantic dependency integrity, and teacher-only answer entities.
- [ ] Implement artifact-independent phases/moves and source-grounded semantic entities.
- [ ] Run `make check-pedagogical-program-ir check-semantic-content-ir`.

### Task 5: Add optimizer, governed tools, and multi-pass synthesis

**Files:**
- Create: `common/contracts/pedagogical_compiler/optimizer.py`
- Create: `common/contracts/pedagogical_compiler/tools.py`
- Create: `common/contracts/pedagogical_compiler/synthesis.py`

- [ ] Test hard-filtering, deterministic receipts, arbitrary-code rejection, and byte-identical unrelated entities after repair.
- [ ] Implement Pareto selection, pure-function tools, typed receipts, verification, selection, and scoped repair.
- [ ] Run `make check-pedagogical-optimizer certify-domain-tools test-semantic-synthesis`.

### Task 6: Wire Artifact Compiler into production generation

**Files:**
- Create: `common/contracts/pedagogical_compiler/artifact_compiler.py`
- Create: `packages/agents/teaching_pack/pedagogical_compiler_runtime.py`
- Modify: `packages/agents/teaching_pack/generate_one_artifact.py`
- Test: `packages/agents/tests/teaching_pack/test_pedagogical_compiler_runtime.py`

- [ ] Test one shared context and complete entity projection accounting.
- [ ] Compile context immediately after `request_from_payload` and compile the artifact before schema validation.
- [ ] Stamp all compiler IDs/hashes/receipts and preserve existing specialist behavior.
- [ ] Run `make check-artifact-compilers check-pedagogical-compiler-waves`.

### Task 7: Verify, emit evidence, close the prior batch, and update next-wave progress

**Files:**
- Modify: `Makefile`
- Generate: `epic-460-compiler-waves.patch`
- Generate: `epic-460-compiler-waves.verification.json`

- [ ] Run every targeted gate and architecture truth gate.
- [ ] Generate the binary-safe patch and SHA-256 evidence.
- [ ] Check blockers and close only #465, #471, #464, #466, #467, #468, #472, and #469 in dependency order.
- [ ] Post an idempotent progress ledger to #470, #473, and #489-#496 naming implemented evidence and remaining live-path/Definition-of-Done gaps; leave them open.
- [ ] Comment on #460 and #488 without closing either Epic.
