# Verdict 04 — Agent Harness & Tool Contracts

## Vấn đề thứ nhất: tool stub vẫn bị bind vào tool-list của LLM

Bảng gốc (mục 12.5) cho thấy tool access bất đối xứng:

| Agent | read_file | write_file | web_search | web_fetch | task |
|-------|-----------|------------|------------|-----------|------|
| Planner | **stub** | — | implemented | — | — |
| Researcher | implemented | — | implemented | implemented | — |
| Content Creator | implemented | implemented | — | — | — |
| Reviewer | **stub** | — | — | — | — |
| Lead Agent | — | — | — | — | **stub** |

Đây không chỉ là "code chưa xong" — đây là một vấn đề harness thật sự, vì cách LLM function-calling hoạt động: nếu `read_file` được **bind vào tool schema** gửi cho model của Planner/Reviewer, model **thấy tool này tồn tại** và có thể quyết định gọi nó trong quá trình reasoning (ví dụ "để chắc chắn, tôi sẽ đọc file X trước khi trả lời"). Khi gọi, nó luôn thất bại — không phải vì input sai, mà vì bản thân tool không được implement. Hệ quả:

1. **Tốn một lượt gọi + token** cho một hành động chắc chắn sẽ fail — không phải retry vì lỗi tạm thời, mà lỗi cấu trúc.
2. **Vi phạm ngầm INVARIANT-03** ("mỗi node là pure function (state) → partial_state"): một tool call luôn-raise khiến node không còn behave như pure transform có thể dự đoán, healing orchestrator phải phân biệt "lỗi vì tool stub" với "lỗi transient thật" — nhưng theo tài liệu, `fail_type` hiện chỉ có 4 giá trị (`validation`/`content`/`score`/`timeout`), không có nhãn nào cho "tool không tồn tại", nên rất có thể bị heal nhầm hướng (ví dụ bị coi là transient → retry vô ích).
3. **Model có thể "lên kế hoạch" dựa trên khả năng ảo**: một tool available-nhưng-luôn-fail tệ hơn không có tool, vì model không biết nó bị hỏng cho tới khi thử.

`task()` là trường hợp cực đoan của cùng vấn đề: `NotImplementedError` tại `tools/task.py:41`, được tài liệu gốc mô tả là "INVARIANT-01 enforcement" — Verdict 01 đã chỉ ra đây là tính năng dở dang đội lốt invariant, không phải enforcement có chủ đích. Verdict này bổ sung góc nhìn harness: **enforcement đúng cách không phải là để một tool tồn tại-nhưng-luôn-raise, mà là không bind tool đó vào model ngay từ đầu.**

## Vấn đề thứ hai: mỗi agent tự viết lại runtime riêng — không có harness dùng chung

Bốn agent (Planner, Researcher, Content Creator, Reviewer) đều tự triển khai lặp lại các khối logic gần giống nhau nhưng không thống nhất:

| Agent | Retry logic | Đặc thù |
|-------|-------------|---------|
| Planner | `critique_lesson()` repair loop tối đa 3 lần, temperature 0.7 → 0.3 khi retry | Riêng biệt trong `lesson_critic.py` |
| Researcher | Retry tối đa 3 lần | Riêng biệt trong `nodes.py` |
| Content Creator | 3 retry attempts với error-feedback prompt | Riêng biệt, gắn với streaming path |
| Reviewer | Không rõ retry policy trong tài liệu | 3 judge calls độc lập (khác concept — không phải retry) |

Không có một `AgentRuntime`/harness layer dùng chung cho: retry+backoff, temperature bump khi retry, cost/token tagging (INVARIANT-07: "All LLM calls include metadata.tags"), lựa chọn streaming vs non-streaming. Mỗi agent module vừa chứa prompt logic, vừa chứa parsing logic, vừa chứa retry/error-handling logic — vi phạm SoC ở cấp độ agent, dù kiến trúc tổng có vẻ modular ở cấp graph.

**Rủi ro cụ thể**: khi cần thay đổi chính sách chung (ví dụ thêm exponential-backoff-with-jitter cho mọi agent, hoặc đổi cách gắn `metadata.tags` để cost attribution chính xác hơn), phải sửa 4 nơi khác nhau, dễ drift — đúng loại vấn đề mà `HealingOrchestrator` (retry ở cấp graph) và retry nội bộ từng agent (ở cấp LLM call) đang chồng chéo trách nhiệm mà tài liệu không phân định rõ ranh giới.

## Vấn đề thứ ba: Reviewer có "hai triển khai" — thêm một lớp trùng lặp harness nữa

Mục 3.5 tài liệu gốc: **Legacy step_10b** (`gates/llm_judge.py`, heuristic scoring, MVP stub) và **Teaching-pack reviewer** (full LLM-as-Judge G-Eval) tồn tại song song, với chữ ký hàm/contract khác nhau. Đây là biến thể khác của smell đã nêu ở Verdict 03 (3-4 hệ thống judge), nhưng nhìn từ góc harness: nếu `llm_judge.py` không còn nằm trên đường live path của teaching-pack graph, nó nên bị xóa theo đúng pattern Verdict 01, không giữ "cho MVP cũ".

## Vấn đề thứ tư: kiểm tra compliance (hard-block/PII/answer-key) không có "chủ nhà" kiến trúc rõ ràng

Các kiểm tra tất định (deterministic) — 9 hard-block, PII detection, answer-key leakage — hiện nằm rải rác: một phần trong `gates/content_reviewer.py` (Lớp 2-3), một phần trong `quality/layer4_judge/hard_blocks.py` (`enforce_hard_blocks()`), và middleware `guardrail` (order=8) cũng làm PII detection ở tầng khác. Ba nơi cùng quan tâm tới an toàn nội dung nhưng không rõ ai là nguồn sự thật, ai gọi ai. Với sản phẩm giáo dục K-12, đây là bề mặt rủi ro compliance — không nên để enforcement bị phân mảnh giữa middleware/gate/judge mà không có sơ đồ trách nhiệm tường minh.

## Verdict

**Chuẩn hoá harness theo hướng contract-first, và tách bạch "đánh giá chủ quan" (LLM judge) khỏi "thực thi chính sách tất định" (compliance) thành hai thành phần kiến trúc riêng biệt.**

1. **Cấm bind tool chưa implement vào LLM tool-list — enforce bằng CI, không bằng convention.** Định nghĩa registry khai báo `packages/agents/harness/capabilities.py`:
   ```python
   class ToolStatus(Enum):
       IMPLEMENTED = "implemented"
       PLANNED = "planned"       # tồn tại trong backlog, KHÔNG được bind
       DEPRECATED = "deprecated" # đang gỡ bỏ, KHÔNG được bind

   AGENT_CAPABILITIES: dict[str, list[ToolSpec]] = {
       "planner": [ToolSpec("web_search", ToolStatus.IMPLEMENTED)],
       "reviewer": [],  # read_file bị loại khỏi bind list, không phải "stub còn đó"
       ...
   }
   ```
   Một test `test_no_unimplemented_tool_bound.py` compile graph thật và assert: mọi tool trong tool-schema thực sự gửi cho LLM đều có `ToolStatus.IMPLEMENTED`. Nếu một khả năng "planned" nhưng chưa xây, nó **không xuất hiện với model** — không phải xuất hiện rồi raise.
2. **Trích xuất `AgentRuntime` harness dùng chung**: một hàm/class tham số hoá (`model`, `system_prompt`, `tools`, `max_retries`, `retry_temperature_schedule`, `streaming`) chịu trách nhiệm retry+backoff, cost tagging (INVARIANT-07), lựa chọn streaming. Mỗi `*_node()` trở thành: build prompt → gọi `AgentRuntime.run()` → parse output theo Pydantic schema riêng. Giảm 4 bản retry-logic gần-giống-nhau xuống 1.
3. **Hợp nhất `read_file`/`write_file`** thành một module FS tool sandbox dùng chung (`packages/agents/tools/fs.py`), với audit log khi Content Creator ghi artifact thật ra đĩa — đây là bề mặt ghi file, cần được coi là security-sensitive tương đương mức độ cẩn trọng của PII middleware.
4. **Thêm `fail_type` mới: `tool_unavailable`** (khác `validation`/`content`/`score`/`timeout`) cho trường hợp hiếm còn sót (ví dụ trong giai đoạn chuyển tiếp trước khi mục 1 hoàn tất) — đảm bảo healing orchestrator không heal nhầm lỗi cấu trúc như lỗi transient.
5. **Đề xuất agent/node mới: `compliance_gate_node`** — một node **tất định, không gọi LLM**, gộp toàn bộ enforcement hiện đang rải rác (9 hard-block + PII + answer-key leakage) làm một bước graph tường minh, chạy **trước** `teacher_approval`, tách biệt hoàn toàn khỏi `reviewer_node` (LLM judge chủ quan). Đây chính là điều team cần khi bổ sung "agent mới": không phải một LLM agent nữa, mà một policy-enforcement node độc lập, dễ audit, dễ test 1-1 (mỗi hard-block một test, chạy qua node thật — đúng yêu cầu cuối checklist Verdict 03), và **trực tiếp hỗ trợ audit-log requirement của Verdict 03 Option A** (tách rõ "auto-approved vì compliance pass" khỏi "auto-approved vì judge score cao").
6. **Xóa `gates/llm_judge.py` (legacy step_10b)** nếu xác nhận không còn trên live path — áp dụng đúng pattern xóa-vật-lý-kèm-guard-test của Verdict 01.

## Checklist hành động

- [ ] Grep toàn bộ nơi tool được bind vào model (`bind_tools`, tool schema construction) cho cả 5 agent
- [ ] Viết `AGENT_CAPABILITIES` registry, loại bỏ mọi tool status != IMPLEMENTED khỏi bind list thực tế
- [ ] Viết `test_no_unimplemented_tool_bound.py`
- [ ] Thiết kế + trích xuất `AgentRuntime` harness dùng chung (retry, backoff, cost tagging, streaming selection)
- [ ] Migrate Planner, Researcher, Content Creator, Reviewer sang dùng `AgentRuntime`
- [ ] Hợp nhất `read_file`/`write_file` vào `tools/fs.py` dùng chung, thêm audit log cho write
- [ ] Thêm `fail_type = "tool_unavailable"` vào `TeachingPackState` fail tracking
- [ ] Thiết kế `compliance_gate_node`: input (artifact_chunks), output (pass/fail + violated rules), không LLM
- [ ] Wire `compliance_gate_node` vào graph trước `teacher_approval`, sau `render_quality`
- [ ] Xác nhận `gates/llm_judge.py` không còn được import ở live path → xóa + guard test
- [ ] Cập nhật bảng "Per-Agent Tool Access" trong ARCHITECTURE.md để phản ánh registry mới (không maintain tay hai nơi)
