# Verdict 08 — Migration Roadmap (thứ tự thực thi thực tế)

> Tổng hợp Verdict 01-07 thành một trình tự thi công có phụ thuộc rõ ràng. Nguyên tắc xuyên suốt (Verdict 00): **big-bang, xóa vật lý, không patch, luôn kèm guard test** — áp dụng cho mọi phase dưới đây trừ khi ghi chú khác.

## Nguyên tắc sắp xếp thứ tự

Ba câu hỏi quyết định một verdict nằm ở phase nào:

1. **Có phải quyết định sản phẩm cần chốt trước khi code không?** (Verdict 03 fast-lane, Verdict 05 circuit breaker scope) → luôn ở Phase 0, chặn mọi phase sau liên quan.
2. **Nó có phải nền tảng mà verdict khác phụ thuộc vào không?** (Verdict 02 state unification là nền cho Verdict 05 scoped-replan đọc `fail_context`; Verdict 06 observability backbone là nền cho Verdict 07 UI) → đi trước.
3. **Nó có zero-risk, zero-dependency không?** (AGENTS.md fix, xóa Lead Agent) → làm ngay, song song với mọi thứ khác, không chờ.

## Sơ đồ phụ thuộc

```
Phase 0 (Quyết định sản phẩm — KHÔNG code)
  ├─► 03: Fast-lane Option A/B
  └─► 05: Circuit breaker scope (ADR)
         │
         ▼
Phase 1 (Zero-risk, chạy song song, không phụ thuộc gì)
  ├─► 01: Xóa Lead Agent + task() stub
  ├─► 01: Xóa 8 middleware PARKED_REACT
  ├─► 01: Cập nhật AGENTS.md
  └─► 01: Policy TTL cho "Parked" status
         │
         ▼
Phase 2 (Nền tảng — mọi phase sau phụ thuộc vào đây)
  ├─► 02: Unify state (xóa OhMyClassState, StageEnum)
  └─► 06: Observability backbone (INVARIANT_REGISTRY, events.py, run_events)
         │
         ▼
Phase 3 (Core correctness — phụ thuộc Phase 2)
  ├─► 03: Judge consolidation (AdaptiveJudge làm entry point duy nhất)
  ├─► 04: Harness chuẩn hoá (AgentRuntime, capabilities registry, compliance_gate_node)
  └─► 05: Scoped replan (đọc fail_context, cần State đã unify ở Phase 2)
         │
         ▼
Phase 4 (Resilience & config hoá)
  ├─► 05: Parallelism cap → config
  ├─► 05: Circuit breaker implementation (theo ADR đã chốt ở Phase 0)
  ├─► 05: 9Router fallback + streaming interruption resilience
  └─► 06: Test taxonomy đầy đủ (contract/unit/e2e/resilience) + CI "component mới kèm test"
         │
         ▼
Phase 5 (UX — phụ thuộc trực tiếp Phase 2 + 3 + 4)
  └─► 07: Explainable gate, live status, escalate notification, post-export revision
```

**Vì sao UX ở cuối dù giá trị người dùng cao**: payload gate mở rộng (Verdict 07 mục 1) cần `revision_count` theo `artifact_id` — chỉ đúng sau khi Verdict 05 scoped-replan chạy đúng granularity (Phase 3). Live status bar (Verdict 07 mục 3) cần `ObservabilityEvent` stream thật sự chạy (Phase 2). Làm UX trước sẽ tạo UI hiển thị dữ liệu giả/rỗng — tệ hơn không làm.

---

## Phase 0 — Quyết định sản phẩm (1-2 tuần, không có code merge)

| Việc | Output | Ai chốt |
|---|---|---|
| Fast-lane vs INVARIANT-06 | Option A (giữ fast-lane, sửa cách diễn đạt + audit + revert) hay Option B (bỏ fast-lane) | Product + Compliance/K-12 safety review |
| Circuit breaker scope | ADR: provider-level + run-level (khuyến nghị Verdict 05) hay khác | Engineering lead + Infra |

**Điều kiện ra khỏi Phase 0**: cả hai quyết định có văn bản (ADR ngắn, tương tự ADR-018 đã có precedent trong hệ thống). Phase 3 và Phase 4 không được bắt đầu phần liên quan nếu Phase 0 chưa chốt.

## Phase 1 — Dọn dẹp zero-risk (có thể chạy song song với Phase 0, ngay lập tức)

Không phụ thuộc quyết định sản phẩm nào. Nên là PR đầu tiên của cả roadmap này vì rủi ro thấp nhất, giá trị traceability cao nhất.

- Xóa Lead Agent (`config.py`, `tools.py`, `recovery.py`, `prompts/system.md`, `task()`), thêm `test_no_lead_agent_runtime.py`
- Xóa 8 middleware `PARKED_REACT`, renumber `order` 1-23, thêm `test_no_parked_middleware_registered.py`
- Cập nhật AGENTS.md
- Thêm policy TTL cho "Parked" status trong CI

## Phase 2 — Nền tảng (3-5 tuần, phụ thuộc: không gì ngoài Phase 1 hoàn tất)

Đây là phase rủi ro kỹ thuật cao nhất (big-bang state migration) nhưng **phải** đi trước Phase 3, vì Verdict 05 (scoped replan) và Verdict 07 (payload gate) đều đọc field mà chỉ tồn tại đáng tin cậy sau khi state được hợp nhất.

1. **State unification (Verdict 02)**: parity test trước → migrate healing/middleware → xóa `OhMyClassState` → `StageEnum` thay 8/9/13.
2. **Observability backbone (Verdict 06, phần schema + writer)**: `INVARIANT_REGISTRY`, `ObservabilityEvent`, bảng `run_events`, wiring cơ bản (chưa cần dashboard đầy đủ — đó là Phase 4/5).

**Gate ra khỏi Phase 2**: parity test giữa `OhMyClassState`/`TeachingPackState` xanh 100% trên tập run lịch sử trước khi xóa; `test_invariant_coverage.py` chạy được (dù chưa đủ 10/10 invariant có test thật — đó là công việc trải dài sang Phase 3-4).

## Phase 3 — Core correctness (4-6 tuần, phụ thuộc Phase 0 + Phase 2)

Ba việc lớn có thể chạy song song bởi các sub-team khác nhau vì chạm vào các module khác nhau, nhưng đều cần State đã unify:

1. **Judge consolidation (Verdict 03)**: shadow-mode `AdaptiveJudge` vs `GEvalScorer` trên historical runs → fold scoring logic → cutover `reviewer_node` → xóa `GEvalScorer`/`pedagogical_scorer.py` khỏi live path.
2. **Harness chuẩn hoá (Verdict 04)**: `AGENT_CAPABILITIES` registry + `test_no_unimplemented_tool_bound.py` → trích xuất `AgentRuntime` → migrate 4 agent → hợp nhất `fs.py` → thêm `fail_type = "tool_unavailable"` → **build `compliance_gate_node`** (node tất định mới, wire trước `teacher_approval`, sau `render_quality`) → xóa `gates/llm_judge.py`.
3. **Scoped replan (Verdict 05)**: sửa `HealingOrchestrator.heal()` đọc `fail_context["artifact_id"]`, scope theo dependency graph fan-out.

**Lưu ý phối hợp**: `compliance_gate_node` (mục 2) và judge consolidation (mục 1) cùng chạm `reviewer_node`/gate ordering — cần một PR tích hợp cuối phase để đảm bảo thứ tự đúng: `render_quality` (AdaptiveJudge) → `compliance_gate_node` (deterministic) → `teacher_approval`.

**Gate ra khỏi Phase 3**: test riêng cho 9/9 hard-block chạy qua đúng production path; test "fail 1 artifact ở wave 2, artifact wave 1 không bị xóa" xanh; `AGENT_CAPABILITIES` không còn tool nào status khác `IMPLEMENTED` bị bind vào LLM.

## Phase 4 — Resilience, config hoá, test taxonomy (3-4 tuần, phụ thuộc Phase 0 + 3)

- Circuit breaker theo ADR đã chốt Phase 0
- Parallelism cap → config file tường minh
- 9Router fallback/health-check bypass (hoặc document rõ nếu ngoài phạm vi `packages/agents`)
- Streaming interruption resilience test (Content Creator)
- Test taxonomy đầy đủ (`tests/guard|contract|unit|integration|e2e|resilience/`), CI policy "component mới bắt buộc kèm test"
- Hoàn thiện 10/10 `INVARIANT_REGISTRY` entries với test thật, đặc biệt INVARIANT-05/06 (an toàn K-12)
- Ops dashboard tối thiểu (escalate/ngày, healing strategy distribution, fast-lane rate, cost/run)

## Phase 5 — UX & Teacher Trust (3-4 tuần, phụ thuộc Phase 2 + 3 + 4)

Toàn bộ Verdict 07: explainable gate payload, fast-lane UI label + revert, live status bar (tiêu thụ `ObservabilityEvent` từ Phase 2/4), escalate notification, post-export revision entrypoint, `teacher_facing_summary` field. Có thể làm incremental/theo sub-feature (không bắt buộc big-bang toàn bộ UX cùng lúc) vì đây là additive UI, không xóa/thay thế cơ chế nền.

---

## Bảng tổng hợp effort & rủi ro

| Phase | Nội dung chính | Rủi ro kỹ thuật | Rủi ro nếu bỏ qua/làm sai thứ tự |
|---|---|---|---|
| 0 | Quyết định fast-lane + circuit breaker scope | Thấp (không code) | Cao — mọi phase sau xây trên giả định sai |
| 1 | Xóa dead code | Rất thấp | Thấp, nhưng technical debt tích lũy tiếp nếu trì hoãn |
| 2 | State unification + observability schema | **Cao** (big-bang trên state authoritative) | Cực cao — Phase 3/5 sẽ phải làm lại nếu state chưa đúng |
| 3 | Judge consolidation, harness, scoped replan | Trung bình-cao (chạm live inference path) | Cao — đây là nơi K-12 safety invariant thật sự được enforce |
| 4 | Resilience, test taxonomy | Trung bình | Trung bình — thiếu test khiến Phase 2-3 không verify được lâu dài |
| 5 | UX | Thấp-trung bình (additive) | Thấp về kỹ thuật, cao về UX/trust nếu trì hoãn quá lâu |

## Về việc bổ sung agent mới

Sau khi rà soát toàn bộ 5 agent hiện có (Planner, Researcher, Content Creator, Reviewer, và Lead Agent đã khai tử), **không có nhu cầu thêm một LLM agent mới**. Thành phần mới duy nhất được khuyến nghị — `compliance_gate_node` (Verdict 04) — **cố ý không phải một agent**: nó là node tất định, không gọi LLM, để tránh lặp lại chính vấn đề mà toàn bộ chuỗi verdict này chỉ ra (quá nhiều hệ thống LLM-judge chồng chéo, Verdict 03). Nguyên tắc: mọi enforcement có thể biểu diễn bằng logic tất định (hard-block, PII, answer-key leakage) nên **ở ngoài** vùng LLM, không phải thêm một judge LLM thứ 5. Nếu trong tương lai team cân nhắc agent mới thật sự (ví dụ một "Localization Agent" cho đa ngôn ngữ, hay "Accessibility Agent" chuyên biệt hoá alt-text/reading-level), nó nên đi qua RFC riêng, dùng `AgentRuntime` harness (Verdict 04) làm nền ngay từ ngày đầu — không lặp lại pattern "mỗi agent tự viết retry logic riêng" đã bị chỉ ra là smell.

## Checklist theo dõi tiến độ tổng (roll-up từ 01-07)

- [ ] Phase 0 hoàn tất: 2 ADR có văn bản, được review bởi product + compliance
- [ ] Phase 1 hoàn tất: Lead Agent + PARKED_REACT xóa vật lý, AGENTS.md đúng, 2 guard test mới xanh
- [ ] Phase 2 hoàn tất: `OhMyClassState` xóa, `StageEnum` là nguồn sự thật duy nhất, `ObservabilityEvent`/`run_events` wired
- [ ] Phase 3 hoàn tất: `AdaptiveJudge` là entry point duy nhất, `compliance_gate_node` live, scoped replan verified bằng test
- [ ] Phase 4 hoàn tất: 10/10 invariant có test thật trong CI, circuit breaker theo ADR, test taxonomy đầy đủ 6 tầng
- [ ] Phase 5 hoàn tất: giáo viên thấy rationale/healing-history tại gate, live status bar hoạt động, escalate có notification
- [ ] Cross-check cuối: chạy lại toàn bộ 10 invariant trong ARCHITECTURE.md mục 12.12, xác nhận mỗi dòng ✅ giờ trỏ tới một test thật, cập nhật bảng đó trong tài liệu kiến trúc chính thức (v2.0)
