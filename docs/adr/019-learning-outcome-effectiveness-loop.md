# ADR-019: Learning-Outcome Effectiveness Loop

## Status

**Decided** (2026-06-30) — Add a longitudinal subsystem that measures whether generated teaching packs actually help students learn, and feeds that signal back into content generation. Grounded in the ULW research synthesis (`.omo/ulw-research/20260630-141939/`). Complements ADR-017 (decomposition) and ADR-018 (runtime parity).

## Context

The system measures **content quality** extensively (6 layers, LLM-as-Judge) but **learning effectiveness not at all** — content quality ≠ "does it teach?". Verified gaps: `packages/quality/layer2_content/pedagogical.py:61` hardcodes all 7 pedagogical metrics to `True` (silent-pass); `student_responses`/`diagnostic_report`/`student_profile`/`student_evidence` exist but are never populated; the pipeline ends at `export_finalize` with no outcome collection; webhook endpoints are TODO stubs.

The primary user is a **private tutor**, not an LMS-using institution — manual score entry is unacceptable ("giảm tải sổ sách", not "thêm dashboard"). The system already has an API-driven Google Forms exporter (OAuth + `createForm` + `batchUpdate`) and `google_forms`/`h5p`/`qti` export formats — a ready auto-capture path.

## Decision

### Topology — a separate longitudinal subsystem, not a pipeline stage

Effectiveness is inherently longitudinal (attempts over weeks) and cross-run (a class's packs accumulate outcomes), so it cannot be a per-run synchronous stage. It is an application-layer subsystem: **outcome store + ingestion + KT engine**. The pipeline **reads** mastery at planning time and **writes** a non-blocking `DeliveryRecord` post-export. Effectiveness is measured **retrospectively** — it can never be a pre-delivery gate; it is a feedback signal that improves *future* packs (RISE continuous-improvement).

### Auto-capture via existing export formats (no manual entry, no bespoke runtime)

Ride the Google Forms exporter: one action creates the whole form (all questions + correct answers + points, quiz-mode auto-grade) and returns the share link; the tutor just shares it. Results are **pulled** via `forms.responses.list`, auto-graded (Forms scores for objective items, LLM via 9router for essays), normalized to `StudentAttempt`, mapped to KC via question `kc_ids`. The **print pack stays offline/no-JS** (invariant intact); Google Forms is a parallel digital channel. H5P/xAPI and Zalo are later channels.

### Knowledge tracing — BKT first

`kt_engine` uses pyBKT (BKT, 4 params/KC, MIT) — cold-start friendly, fits a handful of students. Batch update after each response poll → per-`(student, KC)` mastery + confidence. With sparse data, mastery is low-confidence and consumers **degrade to persona + ClassKnowledgeGraph** (ADR-017). DKT/GKT is a future swap behind the same interface.

### Three knowledge sources for planning

The planner/concept-picker consumes: **declared** (persona / ClassProfile) + **taught** (ClassKnowledgeGraph) + **learned** (KT mastery). KT mastery drives empirical assume-vs-reteach.

### Loop closure

- **Per-student (channel 1):** mastery → planner assume-vs-reteach/concept-picker → next session adapts.
- **Cross-student (channel 2, RISE):** aggregate mastery-gain per (template/methodology × KC) feeds decomposition-memory template ranking (ADR-017 topic-decomposition 014) — effective approaches rise, ineffective ones flagged. Trend over iterations, not single-pack verdicts (attribution is hard — signals are aggregate/advisory).
- **HITL discipline (Plot-Ark 3-layer):** L1 low-risk regen hints auto; L2 effectiveness-driven content changes are teacher-suggested; L3 advisory insights read-only. Effectiveness never silently rewrites content.

### Contrastive concept-alignment verifier (precondition for trustworthy KT)

Per-KC mastery is meaningful only if a question tagged KC-X actually tests KC-X. A contrastive verifier (KT4EQG) uses sibling KCs as hard negatives to judge alignment interpretably ("Q3 aligns with sibling KC-Y") in the reviewer/Layer-4 path; misalignment feeds scoped regeneration. This is also one of the **real** pedagogical metrics replacing the stub.

### Honesty constraints

- De-stub `pedagogical.py`: every metric is a real pre-delivery proxy or explicitly `unmeasured` — never default `True`. "Does it teach?" defers to the KT loop.
- No unverified claims in product copy/computation (the research flagged the 0.4/0.3/0.3 composite and vendor stats as unverified — excluded).
- Effectiveness signals are advisory/aggregate; cold-start suppresses them rather than acting on noise.

### Vietnamese fit

Auto-generate the MoET sổ theo dõi (Thông tư 26/2020: 0–10, ĐĐGtx/gk/ck, nhận xét, ma trận) from outcomes — the "giảm tải sổ sách" payoff. "Hiệu quả dạy học" (QĐ764) shown as the tutor's own improvement view, not external evaluation (no chuẩn-xếp-loại language).

### Privacy (minor data, PDPD 13/2023)

Store pseudonym + KC-mastery + score only (raw responses stay at the source); guardian consent is a precondition before capture; retention/erasure extends the ClassProfile machinery and cascades.

## Consequences

- The system can finally answer "does this teach?", not just "is this good?" — closing the quality-vs-effectiveness gap.
- Zero teacher data entry; the tutor shares a Google Form link and receives an auto-generated MoET sheet.
- KT mastery becomes the empirical third planning source; template effectiveness makes decomposition-memory outcome-driven.
- New minor-data surface — gated by consent, pseudonymized, retention-bound.
- Tracked as `.scratch/effectiveness-loop/` (001 model/privacy, 002 de-stub, 003 Forms delivery+capture, 004 BKT, 005 closure+MoET, 006 contrastive verifier, 007 RISE+HITL). Depends on topic-decomposition KC contracts + scaling-resilience 005.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Auto-capture via existing export formats (chosen) | No manual entry; reuses Google Forms exporter; print-pack invariant intact | Needs response-pull + KC tagging + consent |
| Manual teacher score entry | Trivial | Rejected by the user — adds paperwork, anti-"giảm tải" |
| Bespoke student-facing runtime in the pack | Full control | Violates offline/no-JS print-pack invariant; hosting + minor-data surface |
| Effectiveness as a pre-delivery gate | Symmetric with quality gates | Impossible — learning is measured after delivery; would be fake |
| DKT/GKT from the start | More discriminative | Needs training data we lack; BKT is cold-start friendly, swap later |
| Keep pedagogical stubs | No work | Silent-pass; claims quality never measured — rejected |
