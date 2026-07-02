# Verdict 06 — Testing & Observability Strategy

## Vấn đề nghiêm trọng nhất: bảng 10 invariant là lời tuyên bố, không phải kết quả test

Mục 12.12 trong ARCHITECTURE.md liệt kê 10 invariant, tất cả đánh dấu ✅ với chú thích như "CI enforced", "interrupt() enforced", "Registry enforced". Nhưng xuyên suốt 5 verdict trước, mỗi lần đọc kỹ một invariant, verdict lại phát hiện ✅ đó không hoàn toàn đúng:

- **INVARIANT-01** ("Lead Agent NEVER calls LLM directly") — ✅ vì `task()` raise `NotImplementedError`, nhưng đó là workaround/tính năng dở dang, không phải enforcement chủ đích (Verdict 01).
- **INVARIANT-06** ("Teacher Gate CANNOT be bypassed") — mâu thuẫn ngữ nghĩa trực tiếp với fast-lane auto-approve (Verdict 03) — ✅ chỉ đúng theo nghĩa cú pháp (hàm `interrupt()` được gọi), sai theo nghĩa chức năng.
- **INVARIANT-08** ("Clarification middleware is always last") — "Registry enforced" nhưng không rõ có test nào assert `order == 31` là max, hay đây chỉ là convention mà người thêm middleware mới phải tự nhớ.

Nếu 3/10 invariant có vấn đề khi audit thủ công qua đọc tài liệu, kết luận hợp lý là: **bảng invariant hiện tại là tài liệu mô tả ý định (aspirational), không phải một test suite thật.** Với một hệ thống phục vụ nội dung K-12 — nơi một số invariant (05, 06) trực tiếp là compliance/safety boundary — khoảng cách giữa "được tuyên bố" và "được test" là rủi ro cao nhất trong toàn bộ codebase, cao hơn cả dead code (Verdict 01) hay judge phân mảnh (Verdict 03), vì nó ảnh hưởng tới **độ tin cậy của mọi verdict khác**: nếu không có test, không ai biết chắc một invariant có thật sự giữ đúng sau khi thực hiện các big-bang refactor được đề xuất ở Verdict 01-05.

## Vấn đề thứ hai: `events.py` và `observability/` tồn tại nhưng hoàn toàn không được đặc tả

Mục 11 (Bảng Tra Cứu File Chính) liệt kê `packages/agents/events.py` (Event Bus) và `packages/agents/observability/` như hai thành phần hạ tầng riêng biệt — nhưng không một mục nào khác trong toàn bộ 12 phần tài liệu mô tả chúng làm gì: emit event nào, ai consume, ghi vào đâu, có phục vụ dashboard/alerting nào không. Đây là documentation drift cùng loại với AGENTS.md (Verdict 01), nhưng nghiêm trọng hơn vì nó che giấu một câu hỏi vận hành quan trọng: hệ thống self-healing (mục 8) và circuit breaker (Verdict 05) sinh ra rất nhiều tín hiệu đáng giám sát (`fail_count`, `healing_strategy`, `escalate`, `cost_usd`, `tokens_used`) — nhưng tín hiệu đó có thực sự chảy tới đâu đó quan sát được không, hay chỉ tồn tại trong state của một run rồi biến mất khi run kết thúc?

Không có observability pipeline rõ ràng, các khuyến nghị resilience (Verdict 05 mục 6: "cần metric số run bị escalate/ngày") và trust-flow (fast-lane audit) không có nơi để "hạ cánh" — chúng trở thành yêu cầu treo lơ lửng không ai implement được vì thiếu backbone.

## Vấn đề thứ ba: không có test taxonomy — mọi test đều "pytest" hoặc "Vitest", không phân tầng

Ngăn xếp công nghệ (mục 1) chỉ nói "pytest + Vitest". Không có phân tầng kiểu test pyramid: guard test (dead code), contract test (schema), unit test (pure function: reducer, router), integration test (1 node + mocked LLM), e2e/golden-path (toàn bộ graph qua checkpointer), chaos/resilience test (Verdict 05). Hệ quả cụ thể:

- 4 hàm routing (`route_after_triage`, và 3 conditional seam còn lại) là pure function theo INVARIANT-03, cực kỳ dễ test — nhưng không rõ có test nào bao phủ hết các nhánh (mode=plan_unit vs generate_pack, quality pass/fail, approve/reject) hay không.
- 3 custom reducer (`stable_merge_artifacts`, `stable_merge_workflow_states`, `stable_merge_files`) là logic accumulate theo ID — nếu sai, dữ liệu **im lặng** mất ở parallel branch, đúng loại bug nguy hiểm nhất vì không crash, chỉ thiếu dữ liệu. Không thấy đề cập test riêng cho race/order.
- 4 schema Pydantic (`LessonPlan`, `ResearchBundle`, `ArtifactContent`, `JudgeOutput`) không có golden-fixture round-trip test được nhắc tới — một breaking change ở schema có thể không bị phát hiện cho tới khi production fail ở runtime, giữa một run tốn tiền.

## Verdict

**Xây observability backbone trước, dùng chính backbone đó làm nguồn cho cả invariant-test-registry lẫn (sau này) UI teacher-facing ở Verdict 07 — không xây hai đường ống riêng cho cùng một loại tín hiệu.**

1. **`INVARIANT_REGISTRY` làm nguồn sự thật duy nhất**, cùng tinh thần với `StageEnum` ở Verdict 02:
   ```python
   # packages/agents/testing/invariant_registry.py
   @dataclass(frozen=True)
   class Invariant:
       id: str
       description: str
       test_path: str  # file test enforce invariant này

   INVARIANT_REGISTRY: list[Invariant] = [
       Invariant("INVARIANT-01", "Lead Agent never calls LLM directly", "tests/invariants/test_invariant_01.py"),
       Invariant("INVARIANT-06", "Teacher Gate cannot be silently bypassed", "tests/invariants/test_invariant_06.py"),
       # ... đủ 10, mở rộng khi cần thêm invariant mới
   ]
   ```
   Một meta-test (`test_invariant_coverage.py`) assert: mọi entry trong registry có file test tồn tại **và** file đó thực sự chạy (không `skip`/`xfail`). CI fail nếu một invariant mới được thêm vào ARCHITECTURE.md mà chưa có entry registry tương ứng — biến bảng invariant từ tài liệu mô tả ý định thành nguồn có thể verify.

2. **Định nghĩa `ObservabilityEvent` và làm `events.py` là backbone thật**, không phải file rỗng-nghĩa:
   ```python
   class ObservabilityEvent(BaseModel):
       run_id: str
       teacher_id: str
       event_type: Literal[
           "stage_transition", "gate_decision", "healing_decision",
           "hard_block_violation", "escalate", "cost_accrued",
       ]
       payload: dict[str, Any]
       timestamp: datetime
   ```
   Mỗi node/gate/`HealingOrchestrator` emit event qua `events.py` thay vì chỉ ghi vào state rồi biến mất khi run kết thúc. Event được persist vào bảng Postgres mới `run_events` (cạnh `cost_logs` đã có theo mục 1 tech stack). Đây là nguồn dữ liệu **dùng chung** cho hai đối tượng khác nhau, cố tình không xây trùng lặp:
   - **Ops dashboard** (đội vận hành/engineering): escalate rate/ngày, phân bố `healing_strategy` (retry/rewrite/reroute/replan/escalate), tỉ lệ fast-lane auto-approve, cost/run theo agent.
   - **Teacher-facing live status** (giáo viên, xem Verdict 07): cùng event stream, lọc theo `run_id` của chính giáo viên đó, format lại thành ngôn ngữ non-technical thay vì raw `fail_count`/`healing_strategy`.

3. **Test taxonomy tường minh, mỗi tầng có thư mục riêng** (`tests/guard/`, `tests/contract/`, `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/resilience/` — nội dung resilience đã được đặc tả ở Verdict 05, chỉ cần đặt đúng chỗ ở đây):
   - `tests/contract/`: golden-fixture round-trip cho 4 schema chính, chạy trên mọi PR động tới `common/contracts/*`.
   - `tests/unit/`: 4 hàm routing (toàn bộ nhánh), 3 custom reducer (parallel-branch accumulate correctness — cố ý test race/order để bắt lỗi "im lặng mất dữ liệu").
   - `tests/e2e/`: một "golden-path" chạy toàn bộ Teaching-Pack Graph qua `SqliteSaver` (môi trường staging-like), mock LLM calls bằng fixture responses, assert run đi hết `setup_contract → export_finalize` và pass cả 6 lớp quality gate. Đây là smoke test duy nhất nói được "hệ thống chạy được end-to-end" — hiện không có gì đóng vai trò này.

4. **CI policy: "component mới bắt buộc kèm test"**: một node/gate/middleware/hard-block mới (bao gồm `compliance_gate_node` được đề xuất ở Verdict 04, và scoped-replan logic ở Verdict 05) không được merge nếu không có file test tương ứng — enforce bằng một check đơn giản (diff bao gồm file mới trong `gates/`/`middleware/`/`healing/` nhưng không có file mới tương ứng trong `tests/` → fail CI).

## Checklist hành động

- [ ] Audit thủ công: trong 10 invariant hiện tại, cái nào **thực sự** có test hôm nay (không phải "code tình cờ đúng")
- [ ] Viết `INVARIANT_REGISTRY` + `test_invariant_coverage.py` meta-test
- [ ] Viết đủ 10 file test invariant còn thiếu (ưu tiên INVARIANT-05, 06 — an toàn nội dung K-12)
- [ ] Định nghĩa `ObservabilityEvent` schema, wire vào `events.py`
- [ ] Tạo bảng Postgres `run_events`, viết writer
- [ ] Build ops dashboard tối thiểu: escalate/ngày, phân bố healing strategy, fast-lane rate, cost/run theo agent
- [ ] Viết contract test cho `LessonPlan`, `ResearchBundle`, `ArtifactContent`, `JudgeOutput`
- [ ] Viết unit test cho 4 hàm routing (đủ nhánh) + 3 custom reducer (parallel-branch correctness)
- [ ] Viết golden-path e2e test qua toàn bộ graph (mocked LLM, `SqliteSaver`)
- [ ] Thêm CI check "component mới bắt buộc kèm test" cho `gates/`, `middleware/`, `healing/`
- [ ] Cross-link: dùng chung `ObservabilityEvent` stream làm nguồn cho Verdict 07 (teacher-facing live status)
