# Verdict 07 — UX & Teacher Trust Flow

## Vấn đề nghiêm trọng nhất: giáo viên là "black box operator", không phải người cộng tác

Toàn bộ hệ thống — healing ladder (Verdict 05), fast-lane auto-approve (Verdict 03), 9 hard-block (Verdict 04) — vận hành **phía sau** hai `interrupt()` gate (`unit_approval`, `teacher_approval`). Nhưng theo ARCHITECTURE.md mục 10.3, payload gửi cho giáo viên tại gate chỉ có:

```python
response = interrupt({
    "gate": "teacher_approval",
    "artifacts": state["artifact_chunks"],
    "quality_scores": state["quality_scores"],
    "actions": ["approve", "edit", "reject"]
})
```

Không có `healing_strategy`, không có `revision_count`, không có `rationale` từ judge, không có "artifact X đã được sinh lại 2 lần vì Y trước khi bạn nhìn thấy nó". Giáo viên nhận artifact ở trạng thái cuối cùng như thể nó được tạo ra hoàn hảo ngay từ đầu — trong khi thực tế (Verdict 05, 06) có thể đã có 3 lần retry, 1 lần đổi model, hoặc — sau khi Verdict 05 được áp dụng — 1 artifact bị `replan` scoped trong khi các artifact khác giữ nguyên.

**Hệ quả UX cụ thể:**

1. **Fast-lane (Verdict 03) là bypass vô hình nếu không hiển thị**: nếu một artifact được auto-approve qua trust-score mà giáo viên không thấy dấu hiệu nào khác với artifact họ tự duyệt tay, "trust" không được xây — nó bị **giả định**. Giáo viên không biết mình đang tin tưởng cái gì.
2. **Escalate sau 24h timeout (mục 8 ARCHITECTURE.md) là ngõ cụt im lặng**: không rõ giáo viên có nhận notification nào khi một run bị escalate hay không. Nếu không, run "biến mất" khỏi luồng làm việc của họ mà không giải thích.
3. **Scoped-reject (seam 4, ARCHITECTURE.md 4.2) không có UI tương ứng rõ ràng**: gate `teacher_approval` cho action `reject`, nhưng nếu Verdict 05 hiện thực hoá scoped replan theo `artifact_id`, giáo viên cần cách **reject từng artifact riêng** ("worksheet cần sửa, nhưng lesson thì giữ"), không phải reject-toàn-batch nhị phân như hiện tại.

## Vấn đề thứ hai: không có "đường quay lui" tường minh khi giáo viên không hài lòng sau approve

Gate `teacher_approval` có 3 action: `approve`, `edit`, `reject`. Nhưng sau `export_finalize`, không có gì trong tài liệu mô tả việc giáo viên có thể quay lại, yêu cầu chỉnh sửa một artifact đã xuất, hoặc regenerate một phần cụ thể mà không chạy lại toàn bộ run. Với sản phẩm mà giáo viên là người dùng lặp lại hàng tuần (theo mùa học), thiếu đường quay lui buộc họ phải bắt đầu lại từ đầu cho một thay đổi nhỏ — chi phí ma sát UX cao, và chi phí LLM cao đi kèm (không tận dụng lại `lesson_plan`/`research_bundle` đã pass).

## Vấn đề thứ ba: không có tín hiệu tiến độ trong lúc chờ — 8-9 stage là một "hộp đen thời gian"

Pipeline có 8-9 stage tuần tự (đã cần thống nhất số ở Verdict 02), một số stage tốn hàng chục giây tới vài phút (research với `rigorous` policy tới 10 nguồn, content creator streaming 16384 tokens). Tài liệu không mô tả UI progress nào ngoài kết quả cuối. Không có gì trong ARCHITECTURE.md về SSE/WebSocket payload trung gian (mặc dù kiến trúc tổng mục 2 liệt kê "REST / WebSocket (SSE)" là kênh giao tiếp) — nghĩa là hạ tầng streaming đã tồn tại nhưng UX layer có thể chưa tận dụng nó để hiển thị "đang nghiên cứu... đang viết worksheet... đang chấm điểm..." Đây chính xác là loại tín hiệu mà `ObservabilityEvent` (Verdict 06) được thiết kế để cung cấp — nhưng thiết kế đó chỉ có giá trị nếu có UI tiêu thụ nó.

## Verdict

**Dùng chung một event stream (`ObservabilityEvent`, Verdict 06) cho ba mục đích khác nhau — không xây ba đường ống riêng — và thiết kế gate payload theo nguyên tắc "giáo viên luôn thấy đủ để tin tưởng quyết định của mình, dù họ có cần đọc kỹ hay không".**

### 1. Mở rộng payload `interrupt()` — "explainable gate", không đổi cơ chế gate

```python
response = interrupt({
    "gate": "teacher_approval",
    "artifacts": [
        {
            "artifact_id": a["artifact_id"],
            "artifact_type": a["artifact_type"],
            "content": a["content"],
            "quality_score": a["quality_score"],
            "judge_rationale": a["judge_rationale"],       # từ JudgeOutput.rationale — mới expose ra gate
            "revision_count": a["revision_count"],          # từ fail_count theo artifact_id (Verdict 05)
            "healing_history": a["healing_history"],        # ["rewrite", "reroute"] — human-readable, không raw enum
            "approval_mode": a["approval_mode"],             # "fast_lane_eligible" | "manual_required"
            "trust_score": a.get("trust_score"),
        }
        for a in state["artifact_chunks"]
    ],
    "actions": ["approve_all", "approve_selected", "edit_selected", "reject_selected"],
})
```

`approve_selected`/`reject_selected` theo `artifact_id` thay cho quyết định nhị phân toàn-batch — khớp trực tiếp với scoped-replan/scoped-reject của Verdict 05, và cho phép "worksheet cần sửa, lesson giữ nguyên" thành thao tác một lần bấm, không phải reject-rồi-giải-thích-lại-bằng-text.

### 2. Fast-lane hiển thị rõ ràng, không mập mờ với manual approve

Theo Option A đã chọn ở Verdict 03: khi `approval_mode == "fast_lane_eligible"` và hệ thống tự resume gate, UI **phải** hiển thị nhãn tường minh (ví dụ: "✓ Tự động duyệt — điểm tin cậy 9.2/10 · Xem chi tiết") thay vì trông giống hệt một artifact giáo viên tự tay duyệt. Nút "Xem chi tiết" mở đúng `judge_rationale` + `healing_history` đã có sẵn trong payload trên. Đường revert (undo fast-lane approval trong N giờ đầu, trước khi export thật sự diễn ra ở downstream) là yêu cầu bắt buộc đi kèm, đúng cam kết ở Verdict 03.

### 3. Live status bar — tiêu thụ trực tiếp `ObservabilityEvent` (Verdict 06), lọc theo `run_id`

Không xây pipeline UI riêng. Gateway (`services/gateway`) subscribe `run_events` (Postgres, đã định nghĩa ở Verdict 06) hoặc lắng nghe `events.py` bus trực tiếp, filter theo `run_id` của giáo viên, format lại thành chuỗi trạng thái non-technical qua một bảng ánh xạ tường minh:

| `event_type` (raw) | Hiển thị cho giáo viên |
|---|---|
| `stage_transition` → `post_blueprint_research` | "Đang tìm nguồn tài liệu tham khảo…" |
| `stage_transition` → `artifact_workflow` | "Đang soạn nội dung: {artifact_type}…" |
| `healing_decision` → `rewrite` | "Đang cải thiện lại {artifact_type} theo phản hồi chất lượng…" |
| `gate_decision` → `fast_lane_approve` | "✓ {artifact_type} đã được duyệt tự động" |
| `escalate` | "{artifact_type} cần bạn xem xét — hệ thống đã thử vài cách mà chưa đạt chuẩn" |

Không bao giờ hiển thị nguyên văn `fail_type`, `healing_strategy` enum, hay stack trace — đúng nguyên tắc "cùng event stream, khác tầng ngôn ngữ" đã đặt ra ở Verdict 06.

### 4. Escalate không phải ngõ cụt — luôn có notification + hành động rõ ràng

Khi `escalate=True` sau 24h timeout (mục 8), bắt buộc: (a) push notification/email tới giáo viên qua kênh đã có (out of scope kỹ thuật cụ thể ở đây, nhưng phải tồn tại — nối trực tiếp với checklist "alerting" ở Verdict 05 mục 6), (b) trạng thái run trong dashboard chuyển rõ ràng sang "Cần bạn xem xét" thay vì biến mất khỏi danh sách "đang xử lý", (c) một CTA duy nhất dẫn thẳng tới gate đang chờ, không bắt giáo viên tự tìm.

### 5. "Sửa nhanh" post-export — tận dụng lại state đã pass, không regenerate từ đầu

Thêm hành động `request_revision(artifact_id, feedback)` khả dụng **sau** `export_finalize`, tối đa trong một cửa sổ thời gian hợp lý (ví dụ 30 ngày). Về kỹ thuật: đây là một entrypoint mới vào `artifact_workflow` với `lesson_plan`/`research_bundle` đã có sẵn trong checkpoint (`PostgresSaver`, đã hỗ trợ multi-instance), chỉ regenerate artifact được yêu cầu — chính là scoped-replan logic của Verdict 05 áp dụng lại cho một use case khác (revision sau export thay vì fail trong lúc chạy). Không phải tính năng mới về kiến trúc — tái sử dụng cùng cơ chế.

### 6. Đề xuất bổ sung: `teacher_facing_summary` như một trường output có cấu trúc, không phải formatting ở tầng UI

Thay vì để frontend tự "dịch" `JudgeOutput.rationale` (vốn được viết cho mục đích LLM-judge nội bộ, có thể chứa ngôn ngữ kỹ thuật) sang ngôn ngữ giáo viên, thêm một field trong `JudgeOutput`:

```python
class JudgeOutput(BaseModel):
    overall_score: float
    layer_scores: list[LayerScore]
    critical_issues: list[str]
    passed: bool
    rationale: str                     # nội bộ, kỹ thuật, cho debugging/audit
    teacher_facing_summary: str        # 1-2 câu, ngôn ngữ non-technical, sinh cùng lúc rationale
```

Sinh cả hai trong cùng một LLM call (không tốn thêm call riêng) — tách rõ "giải thích cho máy/dev" khỏi "giải thích cho người dùng cuối", đúng SoC ở cấp độ dữ liệu, không chỉ cấp độ code.

## Checklist hành động

- [ ] Mở rộng `interrupt()` payload tại `teacher_approval` với `judge_rationale`, `revision_count`, `healing_history`, `approval_mode` theo từng `artifact_id`
- [ ] Đổi `actions` từ nhị phân sang `approve_selected`/`reject_selected` theo `artifact_id`, khớp scoped-replan (Verdict 05)
- [ ] Thiết kế UI nhãn tường minh cho fast-lane approve + nút "Xem chi tiết" + đường revert trong cửa sổ thời gian xác định
- [ ] Wire live status bar vào `ObservabilityEvent` stream (Verdict 06), viết bảng ánh xạ event→ngôn ngữ giáo viên
- [ ] Implement notification khi `escalate=True` (email/push, kênh cụ thể do team infra quyết định) + trạng thái "Cần bạn xem xét" trong dashboard
- [ ] Thiết kế + implement `request_revision(artifact_id, feedback)` entrypoint post-export, tái dùng checkpoint đã có
- [ ] Thêm field `teacher_facing_summary` vào `JudgeOutput` schema (`common/contracts/judge_output.py`), sinh cùng lúc với `rationale`
- [ ] Viết test: giáo viên reject 1 artifact trong batch 5 artifact → chỉ artifact đó bị regenerate, 4 artifact còn lại giữ nguyên trong UI
- [ ] User-test (không phải unit test) luồng fast-lane với giáo viên thật: đo mức độ họ hiểu "tại sao artifact này được duyệt mà không cần tôi bấm gì"
