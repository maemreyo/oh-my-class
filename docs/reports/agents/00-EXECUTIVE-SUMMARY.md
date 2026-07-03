# Verdict 00 — Executive Summary

> Đánh giá kiến trúc `packages/agents` (oh-my-class), dựa trên `ARCHITECTURE.md` v1.0 (2026-07-02).
> Đây là index cho 7 file verdict chi tiết + 1 roadmap. Đọc file này trước.

## Điểm mạnh cần giữ lại (đừng big-bang những cái này)

- **Fail-closed thật sự**: gate failure chặn export, không silent pass — đúng nguyên tắc đã tuyên bố.
- **Guard-test pattern cho dead code**: `test_no_legacy_runtime.py` assert module `graph.py` (18-node) không tồn tại. Đây là pattern đúng đắn — vấn đề là nó **chưa được áp dụng nhất quán** cho các phần dead code khác (xem Verdict 01).
- **State reducers tường minh** (`stable_merge_artifacts`, `stable_merge_workflow_states`, `stable_merge_files`) — accumulate theo ID, không mất dữ liệu ở parallel branch. Tốt.
- **Send API fan-out theo wave có phụ thuộc** (lesson → worksheet/quiz/drill → recap) — mô hình đúng cho content có dependency graph.
- **Checkpointer theo môi trường** (Memory → Sqlite → Postgres) — đúng chuẩn production readiness.
- **INVARIANT-02** (packages/agents không import từ services/*, apps/*) được CI enforce — boundary discipline tốt, hiếm gặp ở codebase AI-agent.

## Vấn đề nghiêm trọng nhất — đọc ngay Verdict 03

**Fast-lane trust-score auto-approve tại `teacher_approval` gate từng mâu thuẫn trực tiếp với INVARIANT-06** ("Teacher Gate CANNOT be bypassed"). Phase 0 đã chốt hướng xử lý trong ADR-026: giữ fast-lane nhưng reword invariant thành "cannot be silently bypassed" và chỉ cho phép auto-approve sau `compliance_gate_node`, với audit riêng, nhãn UI rõ ràng và revert window. Phần implementation/test của compliance gate vẫn thuộc Phase 3/5.

## Bảng mức độ ưu tiên

| # | Vấn đề | File chi tiết | Mức độ | Loại big-bang? |
|---|--------|---------------|--------|-----------------|
| 1 | Fast-lane vs INVARIANT-06 | Verdict 03 | 🔴 Critical | Cần quyết định sản phẩm trước |
| 2 | Lead Agent + `task()` stub vẫn sống trong repo | Verdict 01 | 🔴 Critical | Yes — xóa vật lý |
| 3 | 3-4 hệ thống judge song song, chỉ 1 cái được wire | Verdict 03 | 🔴 Critical | Yes |
| 4 | 2 state schema (`TeachingPackState` vs `OhMyClassState`) song song | Verdict 02 | 🟡 Important | Yes, sau khi Verdict 01/03 ổn định |
| 5 | 8 middleware PARKED_REACT lẫn trong 31-layer numbering | Verdict 01 | 🟡 Important | Yes |
| 6 | Tool asymmetry per-agent (`read_file` stub bị lộ ra LLM) | Verdict 04 | 🟡 Important | Yes |
| 7 | `replan` xóa toàn bộ downstream state dù chỉ 1 wave fail | Verdict 05 | 🟡 Important | Yes |
| 8 | Fan-out parallelism cap = 2 (cứng, không rõ nguồn config) | Verdict 05 | 🟢 Moderate | No — config audit |
| 9 | AGENTS.md documentation drift (mô tả Lead Agent còn sống) | Verdict 01 | 🟡 Important | No — nhưng khẩn cấp |
| 10 | Invariant table là tuyên bố, chưa có test 1-1 enforce | Verdict 06 | 🟡 Important | Yes |
| 11 | Teacher không thấy healing-ladder / judge rationale ở UI | Verdict 07 | 🟢 Moderate | Yes (incremental OK) |
| 12 | Circuit breaker threshold scope không được đặc tả | Verdict 05 | 🟢 Moderate | No — cần spec trước |

## Danh sách file

1. `01-dead-code-and-documentation-drift.md`
2. `02-state-model-unification.md`
3. `03-quality-judge-consolidation.md` ← đọc trước tiên
4. `04-agent-harness-tool-contracts.md`
5. `05-scalability-and-resilience.md`
6. `06-testing-and-observability-strategy.md`
7. `07-ux-teacher-trust-flow.md`
8. `08-migration-roadmap.md` ← thứ tự thực thi thực tế

## Nguyên tắc áp dụng xuyên suốt (theo yêu cầu của bạn)

Tài liệu gốc đã tự chứng minh rằng team này **có khả năng** làm big-bang đúng cách: legacy graph 18-node bị xóa vật lý, không patch, kèm guard test ngăn hồi sinh. **Verdict tổng quát của tôi: áp dụng chính xác pattern đó cho mọi "zombie code" còn lại trong hệ thống** — không giữ lại "cho chắc", không comment-out, không feature-flag vĩnh viễn. Nếu một component bị decommission, nó phải biến mất khỏi repo và có test khẳng định điều đó, giống `test_no_legacy_runtime.py`.
