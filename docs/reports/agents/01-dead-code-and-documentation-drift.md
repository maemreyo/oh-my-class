# Verdict 01 — Dead Code & Documentation Drift

## Vấn đề

Hệ thống có **hai lớp zombie code** không được xử lý nhất quán với precedent đã có sẵn (`test_no_legacy_runtime.py` cho legacy 18-node graph):

### 1. Lead Agent — "decommissioned" nhưng vẫn sống trong repo

```
config.py         → LeadAgentConfig (model="gpt-5.4", tools, max_turns)   [Parked]
tools.py           → 4 @tool wrappers (run_planner/researcher/creator/reviewer) [Parked]
recovery.py        → build_recovery_context()                             [Parked]
prompts/system.md  → System prompt 38 dòng                                [Parked]
tools/task.py:41   → def task(...): raise NotImplementedError(...)
```

`task()` là **tool duy nhất** mà Lead Agent gọi được, và nó luôn raise. Tài liệu gốc gọi đây là "INVARIANT-01 enforcement" — nhưng đây **không phải enforcement bằng thiết kế**, đây là tính năng chưa hoàn thiện đội lốt invariant. Nếu ai đó vô tình wire lại Lead Agent (hoặc một sub-agent nào đó gọi `task()` để delegate), production sẽ crash ngay giữa một run tốn tiền, thay vì fail sớm và rõ ràng tại review/CI time.

**Rủi ro cụ thể**: 4 file "Parked" này là surface area chết nhưng vẫn được import, test, lint, và có thể được một dev/agent khác vô tình chỉnh sửa hoặc kế thừa logic từ đó — false sense rằng Lead Agent là một lựa chọn khả dụng.

### 2. AGENTS.md documentation drift

`AGENTS.md` mô tả Lead Agent như đang active. Trong một codebase mà rất có thể chính AGENTS.md được các coding agent (kể cả Claude Code) đọc như nguồn sự thật khi thực hiện thay đổi tự động, đây là **rủi ro kép**: vừa gây nhầm lẫn cho người, vừa có thể khiến một AI agent trong tương lai "sửa chữa" hoặc "khôi phục" Lead Agent vì tưởng nó đang bị lỗi, chứ không phải đã bị chủ đích khai tử.

### 3. 8 middleware PARKED_REACT lẫn trong numbering 1-31

`PARKED_REACT` grouping (8 layer) thuộc kiến trúc ReAct đã decommission, nhưng vẫn nằm trong cùng `order: int (1-31)` với 23 middleware đang active. Không có gì trong `BaseMiddleware` ABC phân biệt rõ trạng thái ACTIVE vs PARKED tại compile-time — người đọc order=23 (`subagent_limit`) phải tra chéo bảng "PARKED_REACT" để biết middleware đó có chạy hay không. Đây là readability hazard trực tiếp vi phạm yêu cầu "high-readability" của bạn.

## Verdict

**Xóa vật lý, không patch.** Áp dụng đúng pattern mà team đã tự chứng minh là làm được với legacy graph:

1. **Xóa Lead Agent hoàn toàn**: `config.py`, `tools.py`, `recovery.py`, `prompts/system.md`, và định nghĩa `task()` trong `tools/task.py`. Nếu concept "delegate sang sub-agent qua LLM controller" có giá trị tương lai, nó nên được **redesign từ đầu** như một RFC mới, không hồi sinh từ code stub 38-dòng-prompt đã lỗi thời.
2. **Thêm guard test đối xứng**: `test_no_lead_agent_runtime.py` — assert module không tồn tại, HTTP 410 nếu có route cũ liên quan. Copy nguyên literal pattern từ `test_no_legacy_runtime.py`.
3. **Xóa 8 middleware PARKED_REACT vật lý**, không chỉ đổi status. Nếu ReAct architecture có khả năng quay lại trong tương lai, đó nên là một branch/tag Git, không phải dead code sống chung với production middleware registry. Thêm `test_no_parked_middleware_registered.py`.
4. **Cập nhật AGENTS.md ngay lập tức**, độc lập với các phase khác — đây là zero-risk, zero-dependency fix, nên làm trước tiên (xem Verdict 08, Phase 0).
5. **Đặt chính sách vòng đời cho "Parked" status**: nếu một component được đánh dấu Parked, nó phải có ngày hết hạn (ví dụ 90 ngày). Sau ngày đó, CI tự động fail nếu component vẫn còn trong repo mà chưa được re-activate hoặc xóa. Tránh lặp lại tình trạng "Parked vĩnh viễn" đang xảy ra với Lead Agent.

## Checklist hành động

- [ ] Xóa `lead_agent/{config,tools,recovery}.py`, `prompts/system.md`
- [ ] Xóa định nghĩa `task()` khỏi `tools/task.py` (hoặc xóa cả file nếu không còn dùng)
- [ ] Viết `test_no_lead_agent_runtime.py`
- [ ] Xóa 8 middleware `PARKED_REACT` khỏi `middleware/registry.py`
- [ ] Viết `test_no_parked_middleware_registered.py`
- [ ] Renumber middleware `order` liên tục (1-23) sau khi xóa, cập nhật INVARIANT-08 reference (Clarification phải luôn là layer cuối — cập nhật số layer cuối)
- [ ] Sửa AGENTS.md — mô tả đúng Teaching-Pack Stage Graph là runtime hiện hành
- [ ] Thêm policy TTL cho status "Parked" trong CI (ví dụ qua một `PARKED_UNTIL` metadata + lint rule)
