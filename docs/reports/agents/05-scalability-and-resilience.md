# Verdict 05 — Scalability & Resilience

## Vấn đề nghiêm trọng nhất: `replan` xóa toàn bộ downstream state dù chỉ 1/N artifact fail

Theo mục 8, khi `fail_count=3`, `HealingOrchestrator` áp dụng chiến lược **replan**: "clear toàn bộ downstream state". Nhưng theo mục 4.2, `artifact_workflow` sinh artifact qua **Send API fan-out 3 wave độc lập** (`lesson` → `worksheet/quiz/drill` → `recap`), và state dùng 3 custom reducer tích lũy theo ID (`stable_merge_artifacts` theo `artifact_id`, `stable_merge_workflow_states` theo `workflow_id`) — nghĩa là kiến trúc state **đã được thiết kế để track thất bại ở granularity từng artifact**, không phải toàn batch.

Nếu `quiz` fail lần thứ 3 trong khi `lesson`, `worksheet`, `drill` đã pass, `replan` hiện tại (theo mô tả) xóa sạch **luôn cả `lesson_plan`, `research_bundle`, và toàn bộ `artifact_chunks` đã thành công** — buộc chạy lại từ `planning_blueprint`. Đây là ba vấn đề cộng dồn:

1. **Lãng phí cost/token thật sự đo được**: lesson + worksheet + drill đã tốn tiền LLM để sinh và đã pass quality gate, nhưng bị vứt bỏ vì một artifact khác fail.
2. **Vô hiệu hóa chính lợi ích của kiến trúc Send fan-out**: fan-out theo wave tồn tại để cho phép các artifact độc lập fail/retry riêng lẻ; nếu healing luôn wipe toàn cục, thiết kế parallel-with-per-ID-reducer trở thành vô nghĩa ở nhánh lỗi.
3. **Rủi ro data loss không cần thiết cho giáo viên**: nếu giáo viên đã bắt đầu xem/góp ý một artifact đã pass trước khi hệ thống replan toàn bộ, trải nghiệm là "biến mất không báo trước" — liên quan trực tiếp tới Verdict 07 (teacher trust).

Gốc rễ: `HealingOrchestrator.heal()` được mô tả chọn strategy dựa trên `fail_count`/`fail_type` **ở cấp run**, không phải cấp `artifact_id`/`workflow_id`. Nhưng field `fail_context: dict[str, Any] | None` đã tồn tại trong `TeachingPackState` — rất có thể đã đủ chỗ để mang theo `artifact_id` gây fail, chỉ là orchestrator chưa dùng thông tin đó để scope hành động replan.

## Vấn đề thứ hai: fan-out parallelism cap = 2, nguồn cấu hình không rõ

Tài liệu nói "Parallelism cap: mặc định 2" nhưng không chỉ ra file config nào sở hữu con số này. Nguyên tắc thiết kế đã tuyên bố "**Config-driven**: hành vi kiểm soát qua YAML/JSON, không magic trong code" — nếu `2` là hardcode trong `artifact_fanout.py`, đây là vi phạm trực tiếp nguyên tắc chính team tự đặt ra. Đây không phải vấn đề nghiêm trọng về đúng/sai (2 có thể là giá trị hợp lý), mà là vấn đề **truy vết được** (traceability): không rõ giá trị này được chọn dựa trên benchmark nào (LLM gateway rate limit? cost control? latency SLA?), nên không ai có cơ sở để thay đổi nó an toàn khi cần scale.

## Vấn đề thứ ba: circuit breaker scope không được đặc tả

Mục 8 mô tả CircuitBreaker 3 trạng thái (closed/open/half-open), "threshold-based" nhưng không nói rõ breaker này scoped theo **cái gì**: toàn hệ thống? theo model/provider? theo `run_id`? theo `teacher_id`? Sự khác biệt này quyết định **blast radius**:

| Scope | Ưu điểm | Rủi ro nếu chọn sai |
|-------|---------|---------------------|
| Global (toàn hệ thống) | Phát hiện outage provider nhanh | Một run lỗi cá biệt (ví dụ artifact quá dài) có thể trip breaker và chặn **mọi giáo viên khác** |
| Per-provider/model | Cô lập theo nguồn gốc lỗi thật (LiteLLM fallback chain đã có khái niệm này ở tầng gateway) | Trùng lặp logic với LiteLLM nếu không phối hợp rõ ràng |
| Per-run | An toàn nhất cho giáo viên khác | Có thể không phát hiện được outage hệ thống rộng đủ nhanh |

Đây đúng là loại quyết định **cần spec trước khi code**, như bảng ưu tiên (mục #12) đã ghi — verdict này không tự chọn thay, mà đặt câu hỏi rõ để team quyết định, kèm khuyến nghị.

## Vấn đề thứ tư: LLM Gateway hai tầng — điểm gãy tiềm ẩn chưa được đặc tả fallback

Kiến trúc dùng LiteLLM Proxy (L1, budget/fallback/cache) → 9Router sidecar (L2, RTK compression, fusion routing) → provider thật. Tài liệu không nói: nếu 9Router (port 20128) down, LiteLLM có bypass thẳng tới provider hay toàn bộ pipeline agent bị chặn? Với một sidecar nằm giữa **mọi** LLM call của **mọi** agent, đây là single point of failure tiềm tàng nếu không có health-checked fallback ở tầng gateway.

## Vấn đề thứ năm: streaming path (Content Creator) chưa rõ resilience khi bị ngắt giữa chừng

Content Creator là agent duy nhất dùng streaming, với `max_tokens=16384` — output dài nhất, thời gian stream dài nhất, cũng là artifact tốn nhiều effort nhất để sinh lại nếu fail. Tài liệu không đặc tả: nếu stream bị ngắt ở giữa (network drop, timeout), retry có resume từ đâu, hay luôn full-restart? Vì output bắt buộc `JSON only` (parse toàn bộ sau khi stream xong), một lần ngắt giữa chừng gần như chắc chắn làm hỏng JSON hoàn chỉnh → retry toàn bộ là hành vi hợp lý, nhưng cần được xác nhận và test rõ ràng, không để ngầm định.

## Verdict

1. **Scoped replan (big-bang, nhưng tận dụng thiết kế đã có sẵn)**: sửa `HealingOrchestrator.heal()` để đọc `fail_context["artifact_id"]` (đã có chỗ trong schema) và khi strategy = replan, chỉ xóa artifact đó + các artifact **phụ thuộc downstream** của nó theo đúng dependency graph đã mô tả ở Send fan-out (`worksheet`/`quiz`/`drill` phụ thuộc `lesson`; `recap` phụ thuộc `lesson` + `quiz`). Đây không phải tính năng mới — chỉ là dùng đúng granularity mà `stable_merge_artifacts`/`stable_merge_workflow_states` đã hỗ trợ sẵn. Giữ full-replan (wipe blueprint) chỉ cho trường hợp fail ở `planning_blueprint`/`post_blueprint_research` — nơi mọi artifact downstream thật sự phụ thuộc.
2. **Di chuyển parallelism cap vào config tường minh** (`config/execution_config.py` hoặc tương đương), có comment nêu rõ căn cứ chọn giá trị (rate limit của LiteLLM/9Router, hoặc cost ceiling), cho phép override theo môi trường. Không đổi giá trị `2` ngay — chỉ làm nó truy vết được trước, đo đạc sau.
3. **Đặc tả circuit breaker scope trước khi code thêm**: khuyến nghị mô hình phân lớp — (a) breaker theo provider/model, phối hợp với LiteLLM fallback chain thay vì trùng lặp, (b) breaker theo `run_id` để cô lập lỗi cá biệt không ảnh hưởng giáo viên khác. Đây là quyết định cần một spec ngắn (ADR), tương tự cách team đã dùng ADR-018 cho quality gate.
4. **Đặc tả fallback khi 9Router down**: LiteLLM nên có khả năng bypass sidecar khi health-check thất bại, kèm alerting. Cần xác nhận với team hạ tầng đây có phải trách nhiệm của `packages/agents` hay của tầng gateway/infra riêng — nếu ngoài phạm vi, ít nhất cần ghi rõ trong ARCHITECTURE.md như một known dependency risk thay vì im lặng.
5. **Viết test resilience cho streaming interruption**: giả lập ngắt stream giữa chừng, xác nhận hệ thống fail rõ ràng (không parse JSON rác) và retry đúng theo policy đã thống nhất ở Verdict 04 (`AgentRuntime`).
6. **Xác nhận 24h interrupt timeout → escalate có dead-letter/alerting**, không chỉ đổi state ngầm — nối với Verdict 07 (giáo viên cần thấy) và Verdict 06 (cần metric số run bị escalate/ngày).

## Checklist hành động

- [ ] Đọc code `HealingOrchestrator.heal()` thật, xác nhận `fail_context` đã mang `artifact_id`/`workflow_id` hay chưa
- [ ] Implement scoped replan dùng dependency graph của Send fan-out (lesson → worksheet/quiz/drill → recap)
- [ ] Viết test: fail 1 artifact ở wave 2, assert artifact đã pass ở wave 1 KHÔNG bị xóa
- [ ] Audit nguồn giá trị `parallelism cap = 2`, di chuyển vào config file tường minh
- [ ] Viết ADR về circuit breaker scope (provider vs run vs global), review với team trước khi code
- [ ] Xác nhận cơ chế fallback khi 9Router sidecar down; document hoặc implement health-check bypass
- [ ] Viết test resilience streaming-interruption cho Content Creator
- [ ] Xác nhận + document alerting cho run bị auto-escalate sau 24h timeout
- [ ] Thêm `fail_type = "tool_unavailable"` (tham chiếu Verdict 04) vào cùng luồng healing để tránh heal nhầm
