# Verdict 02 — Hợp Nhất State Model

## Vấn đề

Hệ thống có hai state schema đồng tồn tại:

- **`TeachingPackState`** (`teaching_pack/nodes.py`) — authoritative, TypedDict đầy đủ field cho toàn bộ pipeline (planning, research, content, quality, gate tracking, healing, export, metadata).
- **`OhMyClassState`** (`state.py`) — legacy, vẫn được dùng bởi **healing** và **middleware** layers, "nhiều field trùng lặp nhưng cấu trúc khác nhau" (nguyên văn tài liệu gốc).

### Tại sao đây là vấn đề nghiêm trọng, không chỉ là "công nợ kỹ thuật thông thường"

`HealingOrchestrator` là thành phần chịu trách nhiệm quyết định retry/rewrite/reroute/replan/escalate — tức là nó **ra quyết định vận hành dựa trên state**. Nếu nó đọc `OhMyClassState` trong khi graph nodes ghi vào `TeachingPackState`, bắt buộc phải tồn tại một lớp adapter/mapping ở đâu đó (không được mô tả trong tài liệu kiến trúc — bản thân đây đã là một dấu hiệu xấu: một thành phần quan trọng tới mức quyết định retry-hay-escalate mà không được document tường minh).

Hai kịch bản rủi ro cụ thể:
1. **Field drift**: một field mới thêm vào `TeachingPackState` (ví dụ `quality_recovery_route`) không được đồng bộ sang `OhMyClassState` → healing orchestrator ra quyết định dựa trên dữ liệu cũ/thiếu.
2. **Silent stale read**: nếu adapter mapping chỉ chạy một chiều hoặc tại một thời điểm cố định, middleware Quality Tier (curriculum_alignment, pedagogical_quality, bias_detection...) có thể đang chấm điểm trên một snapshot state cũ hơn thực tế graph đang có — vi phạm trực tiếp nguyên tắc "Fail closed" đã tuyên bố, vì lúc đó gate có thể pass dựa trên dữ liệu sai.

### Vấn đề phụ: numbering không nhất quán trong chính tài liệu

- Mục lục gọi "Teaching-Pack Stage Graph (8 stages)"
- Section 4.2 tiêu đề "9 Stage (Linear Wiring)"
- `TeachingPackState.current_step: int  # 1-13`

Ba con số khác nhau (8 / 9 / 13) cho cùng một khái niệm "bước trong pipeline". Đây không phải lỗi chính tả — nó phản ánh rằng khái niệm "stage" hiện không có **một nguồn sự thật duy nhất** (single source of truth) được code hóa; rất có thể `current_step` tính cả side-branch (`unit_planning`, `unit_approval`) và các recovery loop-back mà biểu đồ tuyến tính 9-stage không thể hiện.

## Verdict

**Big-bang unify, không patch mapping layer.**

1. **Xóa `OhMyClassState`, migrate healing + middleware để tiêu thụ trực tiếp `TeachingPackState`.** Không giữ compat layer nội bộ — nếu healing/middleware cần field mà `TeachingPackState` chưa có, thêm field đó vào `TeachingPackState` (nó đã là authoritative, đây đúng là chỗ nó nên nằm).
2. Nếu có external/legacy consumer thực sự cần shape `OhMyClassState` (ví dụ một service ngoài `packages/agents` — dù INVARIANT-02 nói không ai import trực tiếp, có thể có consumer qua API), viết **một hàm translation duy nhất** ở boundary (API response serialization), không rải mapping logic trong nội bộ pipeline.
3. **Thay 3 con số 8/9/13 bằng một `StageEnum` duy nhất** làm nguồn sự thật; sinh bảng trong tài liệu từ enum đó (docs-as-code) thay vì maintain tay 3 chỗ khác nhau. `current_step` trong state nên là `StageEnum` member, không phải `int` thô — tăng type-safety và tự động đồng bộ doc/code.
4. Viết test **round-trip parity** trước khi xóa `OhMyClassState`: chạy song song cả hai state trên một tập run lịch sử, assert mọi field tương ứng khớp nhau, để phát hiện chỗ nào đang bị drift trước khi cắt bỏ (an toàn hơn xóa mù).

## Checklist hành động

- [ ] Liệt kê đầy đủ mọi nơi `OhMyClassState` được đọc/ghi (grep toàn bộ `healing/`, `middleware/`)
- [ ] Viết test parity giữa `OhMyClassState` và `TeachingPackState` trên dữ liệu run thật (chạy trước khi xóa, làm safety net)
- [ ] Migrate `HealingOrchestrator` sang đọc/ghi `TeachingPackState`
- [ ] Migrate toàn bộ middleware sang `TeachingPackState`
- [ ] Xóa `state.py` (`OhMyClassState`) + thêm guard test tương tự Verdict 01
- [ ] Định nghĩa `StageEnum` duy nhất, refactor `current_step` sang dùng enum này
- [ ] Cập nhật mọi chỗ trong docs (mục lục, section 4.2, state schema) để tham chiếu cùng một con số nguồn (nên auto-generate)
