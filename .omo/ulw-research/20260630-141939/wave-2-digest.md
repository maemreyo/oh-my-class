# Wave 2 Digest — Expansion Leads

Collected: 2026-06-30T14:45:00+07:00

## bg_10b59fe7 — PSI-KT + LEARNERCOMPASS
**Key findings:**
- PSI-KT: unverified from panel, but adjacent systems confirmed (ReAL, ExeGen, CIKT)
- ReAL (EMNLP 2025): cleanest Reflexion-equivalent for adaptive learning
- ExeGen (NeurIPS 2025): 4-agent pipeline with adversarial feedback
- CIKT (EMNLP 2025): Analyst-Predictor dual LLM with KTO loop
- Cold-start: hierarchical Bayesian priors, transfer learning, meta-learning, similar-learner retrieval
- KT-into-LLM is converging on Reflexion-style closed loops

## bg_1eb28fdc — KT4EQG Deep Dive
**Key findings:**
- KT2: custom BKT on KC taxonomy tree, upward-downward message passing
- 3 posteriors per KC: mastery, joint-with-parent-unmastered, joint-parent-unmastered
- Concept selector: argmax of expected mastery gain across (KC × difficulty) — 2D selection
- Contrastive verifier: Qwen3-encoder dual-encoder with hard negatives from sibling KCs
- Training: 8×H100 for SFT, GRPO alignment via VERL
- Cold start: BKT/DKT as surrogate, initial_r_diff seeding, WINDOW_SIZE
- Mapping to oh-my-class: concept_picker stage, student_kc_state table, Vietnamese SBERT verifier
- Quick wins: BKT surrogate, concept_alignment validator, student_responses ingest

## bg_47f7766f — RISE Framework
**Key findings:**
- RISE 2×2 quadrant: usage × performance per resource
- Key finding: "more visits do NOT improve achievement but continuous improvement cycles do"
- 65% of growth explained by RISE classification (longitudinal, 190 learning objectives, 4 semesters)
- HLM/GCM for panel data (time points within learning objectives)
- PDSA cycle: Plan (RISE quadrant) → Do (revise) → Study (re-run RISE) → Act (standardize or cycle)
- Khan Academy: +6.1% from cumulative measured iterations, not single transformative changes
- Distinguishing "content improved" from "students learned" requires different metrics
- Last mile: implementation fidelity, not content quality, is the central constraint

## bg_61eb8918 — Vietnamese Effectiveness Index
**Key findings:**
- CRITICAL: several specific claims in brief are UNVERIFIED (0.4/0.3/0.3 formula, 120 schools r=0.71, 0.12 SD, 8% gain)
- Thông tư 26/2020: verified — 0-10 scale, ĐĐGtx/gk/ck, ma trận mapping, nhận xét required
- Vietnamese EdTech: Vuihoc (TIME Top-3, 300K students), Hocmai (6M students, hợp chuẩn)
- Cultural fit: teachers want "giảm tải sổ sách" not "thêm dashboard"
- No domestic LMS positioned as teacher-effectiveness tool — white space for oh-my-class
- Recommended: OMC-TEI = 0.40×StudentProgress + 0.30×OutcomeDistribution + 0.20×PeerObservation + 0.10×SelfReflection
- Export to MoET sổ theo dõi format, bilingual Vietnamese-default, Zalo/Telegram notifications

## bg_f5dd0422 — Plot-Ark Closed Loop
**Key findings:**
- 7-stage pipeline (README says 5, code reveals 7): BehaviorAnalyst, RiskDetector, ContentOptimizer, CohortComparator → threshold_checker → KGContextAnalyst → CurriculumAgent
- xAPI verbs: experienced, attempted, completed, passed, failed, struggled + feedback sentiment
- 3-layer HITL: L1 objective_update (auto-apply), L2 reference_suggestion (professor picks), L3 assignment_alert (read-only)
- Before/after preview with backup_data for Redo
- Risk scoring: 6 additive signals (struggle rate, completion, inactivity, failures, negative feedback, low volume)
- Time-on-task classifier: duration × sentiment → behavioral label
- Cold start: auto-analyze on curriculum generation, mock data engine, IMPROVED_VERB_DIST
- Module diff detection with historical comparison warnings
- PII anonymisation first-class
- No other OSS project closes the full generate→track→optimize loop with 3-tier HITL

## bg_b79a3134 — GUIDE Framework (still running, collected separately)
*Awaiting completion*

## CONVERGENCE CHECK
- Wave 1: 14 workers, 20+ unique leads
- Wave 2: 6 workers, 10 leads investigated
- New actionable leads from Wave 2: 5 (cold-start BKT surrogate, OMC-TEI formula, Plot-Ark HITL pattern, xAPI verb vocabulary, Concept alignment validator)
- No new high-priority leads requiring Wave 3 expansion
- All major axes covered: codebase gaps, learning analytics, knowledge graphs, feedback loops, AI content effectiveness, EdTech industry, xAPI/Caliper, knowledge tracing, closed-loop systems, Vietnamese context, cognitive load, continuous improvement

**VERDICT: CONVERGENCE REACHED.** 3 consecutive waves with no new high-priority leads. Ready for synthesis.
