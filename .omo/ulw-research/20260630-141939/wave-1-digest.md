# Wave 1 Digest — Learning-Outcome Effectiveness Loop

Collected: 2026-06-30T14:25:00+07:00

## Codebase Workers (4/4)

### bg_b880d627 — Quality & Outcome Tracking (explore)
**Key findings:**
- 6-layer quality gate system measures CONTENT QUALITY only — zero measurement of learning effectiveness
- StudentResponse, DiagnosticReport, StudentProfile contracts exist but are PRE-delivery only (input to diagnose_then_generate)
- 7 pedagogical metrics in layer2_content/pedagogical.py are ALL TODO STUBS (always return True)
- RunContract.student_evidence field exists but is never populated
- No "effectiveness", "feedback_loop", "student_outcome" in git history
- No ClassKnowledgeGraph anywhere in codebase

### bg_9a66387d — State Schema Gaps (explore)
**Key findings:**
- OhMyClassState has ZERO post-delivery learning outcome fields
- TeachingPackState is even slimmer — no diagnostic fields at all
- StudentResponse is write-once, never read back
- No outcome columns in Run or Artifact DB models
- AssessmentCheckpoint in lesson_plan.py is declarative only — never triggers measurement
- The 3 unused state fields (student_responses, diagnostic_report, student_profile) were designed for this purpose but never populated

### bg_83183d2f — Quality Gates Deep Dive (explore)
**Key findings:**
- Layer 1 (schema): Fully implemented, binary pass/fail
- Layer 2 (content): 7 pedagogical metrics ALL STUBS, FACT protocol STUB, age_check STUB; readability_checker and component_scorer implemented
- Layer 3 (HTML): Fully implemented, 6 hard blocks
- Layer 4 (LLM Judge): Full AdaptiveJudge exists but legacy pipeline uses HEURISTIC scoring (word count + section titles)
- Layer 5 (HITL): Implemented, teacher gate
- Layer 6 (Export): Partially implemented
- render_quality() hardcodes "overall": 8.0 when no gate injected — silent bypass
- calibrate_gates() raises NotImplementedError

### bg_5324c1ba — Teaching Pack Graph Extension (explore)
**Key findings:**
- 8-stage graph ends at export_finalize → END — NO post-export stage exists
- make_stage_node() factory pattern — adding new stage requires: stages.py enum + TEACHING_PACK_STAGES tuple + match arm + worker
- EffectivenessMeasurementSink Protocol would be the DI seam (same pattern as QualityGate)
- events.py is in-process SSE — NOT suitable for inbound outcome data
- webhooks/ directory exists but is NOT implemented (no __init__.py)
- Quality routing can be extended with new recovery keys
- Need new SQLAlchemy model + Alembic migration for EffectivenessOutcome

## Web Research Workers (10/10)

### bg_a47ea73d — Learning Analytics Frameworks (librarian)
**Key findings:**
- Greller & Drachsler (2012) generic LA framework: 6 dimensions
- RISE Framework: continuous improvement cycles matter more than raw usage (65% growth)
- Kirkpatrick 4 Levels: oh-my-class partially implements L1 (teacher approval) and L2 (quality scoring)
- CIPP model maps directly to teaching-pack pipeline stages
- Bloom's Mastery: feedback-corrective-enrichment cycle is the proven mechanism
- LA Learning Gain Design (LALGD) model: 3-level framework for aligning data capture with pedagogy
- DCHGNN (2026): causal effect estimation of learning resources using graph neural networks

### bg_b059b52c — Knowledge Graphs in Education (librarian)
**Key findings:**
- ClassKnowledgeGraph prototype exists on GitHub (edusys/class-knowledge-graph) — Java/JanusGraph
- Khan Academy Knowledge Map: ~4k concepts, Neo4j, BKT + shortest-path
- ALEKS: Knowledge Space Theory implementation, knowledge lattice
- PSI-KT (ICLR 2024): joint learning of knowledge states AND prerequisite graphs
- Graph-Based Knowledge Tracing (GKT): GAT over prerequisite DAG
- Vietnamese Curriculum KG exists (opendata.edu.vn/ckg/sparql)
- pyBKT library (Carnegie Mellon): 6 BKT variants, scikit-learn compatible

### bg_2bcbe4c3 — Feedback Loops in Education (librarian)
**Key findings:**
- Formative assessment feedback loops: AI-driven conversational pulses → teacher insights
- SOFIA framework: service-oriented hybrid adaptivity with continuous feedback
- Real-time student response systems improve metacognition
- Gap between content quality and learning effectiveness: aesthetic quality ≠ learning gains
- A/B testing in education: Google Classroom "Experimenter" feature (2026 beta)
- Item analysis: difficulty index, discrimination index → content revision triggers
- Adaptive learning platforms: Knewton, Carnegie Learning, IXL

### bg_4e573e4f — AI Content Effectiveness (librarian)
**Key findings:**
- LLM Feedback RCT (21,478 students): 16% more likely to correct answer, 7% more likely to succeed next problem — BUT only for lower-knowledge students
- LearnLM RCT (Google DeepMind): +5.5pp on novel problems — "durable and transferable understanding"
- Performance ≠ Learning distinction (2026): immediate post-tests overestimate learning
- GenAI meta-analysis (Nature 2026): g=0.40 academic, g=0.72 higher-order thinking
- EduLoop-Agent: closed-loop Diagnosis → Recommendation → Feedback
- EduRL-GPT: +12.8% learning gain via PPO reinforcement learning
- Plot-Ark: xAPI tracking + 5-node analytics pipeline + Curriculum Agent for module edits
- Khan Academy 6-month optimization: +6.1% next-item correctness through incremental improvements

### bg_43ea487c — EdTech Industry Effectiveness (librarian)
**Key findings:**
- Khan Academy: 0.12-0.47 SD gains across multiple RCTs; dosage ≥30 min/week critical
- Duolingo: 0.22 SD from adaptive engine; CEFR-aligned proficiency gains
- ALEKS: 0.19-0.22 SD; Knowledge Space Theory validated
- Cognitive Tutor: 0.16-0.21 SD across 12 RCTs
- Vietnamese EdTech: 0.08-0.12 SD (Vuihoc, Hocmai, VietJack)
- Meta-analyses: average 0.17-0.22 SD for adaptive systems
- Implementation fidelity is the central constraint — not content quality

### bg_d20aa2a7 — xAPI/Caliper Standards (librarian)
**Key findings:**
- xAPI (IEEE 9274.1.1-2023): Actor-Verb-Object statements, Learning Record Stores
- Caliper Analytics v1.2: 16+ metric profiles (Assessment, Media, Reading, Grading)
- Bersin 5-Stage Model: Reaction → Learning → Application → Impact → ROI
- Philips ROI Model: cost-benefit from outcome data
- LTSI: standard instrument for measuring transfer
- Open-source LRS: Learning Locker, Yet Analytics
- Data model patterns: competency mapping via statement + context + result

### bg_d9596f4f — Knowledge Tracing Models (librarian)
**Key findings:**
- BKT: HMM with 4 parameters (prior, learn, guess, slip); pyBKT library (249 stars, MIT)
- DKT: LSTM over interaction sequences; AUC ~0.82 on ASSISTments
- DKVMN: Key-value memory networks; concept-level tracing
- SAKT: Self-attention with causal mask; captures past interactions
- PSI-KT (ICLR 2024): hierarchical state-space, jointly learns KT + prerequisite graphs
- KT4EQG (2026): KT-guided question generation — EXACTLY the pattern oh-my-class needs
- pyKT-toolkit: 30+ DLKT models, comprehensive benchmark
- adaptivetesting library: full CAT with content balancing
- BKT wins on RMSE, DKT wins on AUC — depends on use case

### bg_e415309f — Closed-Loop Content Systems (librarian)
**Key findings:**
- EduLoop-Agent: Neural Cognitive Diagnosis → Adaptive Testing → LLM feedback
- EduRL-GPT: PPO reinforcement learning, +12.8% learning gain
- LEARNERCOMPASS: multi-model path planning + Graph-RAG + Reflexion mechanism
- Pxplore: GRPO reinforcement learning with pedagogical reward function
- Plot-Ark: full loop — Learner Profiling → Path Planning → Adaptive Delivery → Analytics → Module Edits
- Spaced repetition: SM-2/SM-18 algorithms adjust intervals based on recall probability
- Item analysis: difficulty index + discrimination index → flag items for revision
- Contextual bandits: LinUCB for real-time content sequencing
- Closed-loop signals: mastery Δ > 0.15, attempts ≤ 1.8, hint-use < 20%, retention ≥ 70%

### bg_ed893104 — Vietnamese Education Assessment (librarian)
**Key findings:**
- QĐ 764: defines "hiệu quả dạy học" as avg ≥ 70%, 75% lớp đạt mức "đủ"
- Thông tư 26/2020: mandates formative assessment + annual reporting
- Chương trình 2018: competency-based curriculum, requires learning journals/portfolio
- Vietnamese EdTech: Vuihoc (0.12 SD), Hocmai (8% score gain), VietJack (0.45 SD TOEFL)
- Cultural factors: teacher authority, collectivist orientation, resistance to data-driven approaches
- Data silos: most schools use paper-based grade books
- Standardization gap: no national data schema for learning analytics
- Composite effectiveness index proposed: 0.4×avg + 0.3×progress + 0.3×teacher_feedback

### bg_ff07b982 — Cognitive Load & Multimedia Learning (librarian)
**Key findings:**
- CLT: 3 types of cognitive load (intrinsic, extraneous, germane)
- Expertise reversal effect: d=0.505 for novices, d=-0.428 for experts (meta-analysis)
- Worked examples + fading: best practice for novice learners
- Self-explanation effect: good students generate 15.3 explanations/example vs 2.8 for poor
- Mayer's 15 multimedia principles with effect sizes (d=0.36 to 1.67)
- GUIDE framework: 10 archetypes, 60 dimensions for LLM-as-judge instructional quality
- LecEval: ML-trained metric for automated presentation evaluation
- CLPR: 6-strand rubric with CLT guardrails (expertise reversal check)
- Automated Mayer checking: emerging field, no production system yet

## NEW LEADS FOR WAVE 2

1. **KT4EQG** — The exact "KT-guided content generation" loop oh-my-class needs
2. **Plot-Ark** — Full closed-loop with xAPI + analytics + Curriculum Agent
3. **RISE Framework** — Continuous improvement cycles outperform raw usage
4. **EduRL-GPT** — PPO reinforcement learning for content optimization
5. **PSI-KT** — Joint KT + prerequisite graph learning
6. **GUIDE Framework** — LLM-as-judge for instructional quality (Mayer-grounded)
7. **Vietnamese Composite Effectiveness Index** — Adapt for oh-my-class
8. **ClassKnowledgeGraph prototype** — Java/JanusGraph implementation
9. **LEARNERCOMPASS** — Multi-model path planning + Graph-RAG
10. **Pxplore** — GRPO RL with pedagogical reward
