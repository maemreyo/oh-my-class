# Verdict 03 — Quality/Judge Consolidation (🔴 Đọc file này trước tiên)

## Phát hiện nghiêm trọng nhất: Fast-lane mâu thuẫn với INVARIANT-06

Tài liệu gốc, mục 4.2, mô tả gate `teacher_approval`:

> "Duyệt nội dung artifact — approve **với fast-lane (trust-score auto-approve)**, reject, edit"

Tài liệu gốc, mục 12.12, liệt kê:

> INVARIANT-06: "Teacher Gate CANNOT be bypassed" — ✅ Enforced (`interrupt()` enforced)

Hai câu này **mâu thuẫn ngữ nghĩa trực tiếp**. Một cơ chế "trust-score auto-approve" có nghĩa: khi trust score đủ cao, nội dung được duyệt **mà không có con người nào bấm nút approve**. Dù về mặt kỹ thuật `interrupt()` có thể vẫn được gọi (nên "enforced" theo nghĩa hẹp: hàm interrupt được invoke), nhưng nếu fast-lane logic tự động resume nó bằng `approve` mà không có hành động thật của giáo viên, thì **gate đã bị bypass về mặt chức năng**, chỉ không bị bypass về mặt cú pháp code.

Trong bối cảnh sản phẩm là nội dung giáo dục K-12, với các invariant khác liên quan trực tiếp (INVARIANT-05: answer key phải nằm trong `teacher_only`; middleware `guardrail` phát hiện PII; 9 hard-block bao gồm `answer_key_leakage`, `pii_leakage`), việc một artifact có thể **đi thẳng ra học sinh mà chưa có con người xác nhận** là rủi ro compliance/an toàn thực sự, không chỉ là vấn đề code style.

### Đây không phải bug để engineering tự sửa

Đây là quyết định sản phẩm cần chốt trước:

- **Option A — Fast-lane là tối ưu UX hợp lệ**: giữ nó, nhưng đổi cách diễn đạt INVARIANT-06 thành chính xác hơn (ví dụ: "Teacher Gate cannot be silently bypassed — auto-approval qua trust-score là một quyết định được audit, hiển thị rõ, và có thể revert"). Bắt buộc kèm theo: audit log bắt buộc (middleware #9 `teacher_audit_log` đã có sẵn, cần đảm bảo nó ghi rõ "auto-approved via fast-lane, trust_score=X" chứ không lẫn với approve thủ công), UI hiển thị rõ ràng (xem Verdict 07), và đường revert dễ dàng.
- **Option B — Gate thực sự không được bypass**: bỏ fast-lane, mọi artifact luôn chờ con người, có thể bù lại bằng cách rút ngắn review time (surface rationale/score rõ hơn — xem Verdict 07) thay vì bỏ qua review.

**Verdict của tôi: chọn Option A về mặt sản phẩm (fast-lane có giá trị UX thật, giáo viên không nên phải duyệt tay mọi worksheet an toàn tuyệt đối), nhưng bắt buộc phải sửa lại cách invariant này được diễn đạt và enforce, để "✅ Enforced" trong tài liệu là sự thật, không phải wishful documentation.**

## Vấn đề thứ hai: Judge/Scoring bị phân mảnh thành 3-4 hệ thống song song

| Hệ thống | Trạng thái | Năng lực |
|---|---|---|
| `GEvalScorer` (`layer4_judge/geval.py`) | **Active**, dùng bởi `reviewer_node` | G-Eval 3-layer weighted (format 15% / content 55% / presentation 30%), 3 judge độc lập + majority vote, 4 bias mitigation |
| `LiveReviewerQualityGate` (`sub_agents/reviewer/live_quality_gate.py`) | Trạng thái không rõ ràng trong tài liệu | Deterministic lenses (format/content/pedagogy/presentation) + ReviewerCalibration |
| `AdaptiveJudge` (`layer4_judge/judge_interface.py`) | **Exported nhưng chưa wired** | RubricSelector + hard-block enforcement đầy đủ — theo mô tả, đây là hệ thống **hoàn chỉnh nhất** nhưng không chạy trong production |
| `pedagogical_scorer.py` | Tách biệt, không kết nối `GEvalScorer` | 5-dimension pedagogical scoring riêng |
| `hard_blocks.py` (`enforce_hard_blocks()`) | Tồn tại, nhưng tài liệu không nói rõ layer nào gọi nó trong đường live | 9 hard-block rules |

Đây là smell rõ ràng: **hệ thống mạnh nhất về mặt thiết kế (`AdaptiveJudge`) lại không phải hệ thống đang chạy thật**. Điều này thường xảy ra khi một refactor bị bỏ dở giữa chừng — y hệt pattern của Lead Agent (Verdict 01). Hệ quả trực tiếp: 9 hard-block rules được thiết kế (bao gồm những rule an toàn quan trọng như `answer_key_leakage`, `pii_leakage`, `teacher_gate_not_approved`) **có thể không được enforce nhất quán** nếu đường live path (`GEvalScorer`) không gọi `enforce_hard_blocks()` theo cùng cách `AdaptiveJudge` làm.

## Verdict

**Chọn một pipeline duy nhất làm production path, xóa các pipeline còn lại — không giữ "để dự phòng".**

1. **Chọn `AdaptiveJudge` làm entry point duy nhất của `reviewer_node`** — vì theo mô tả nó là bản đầy đủ nhất (RubricSelector + hard-block enforcement tường minh).
2. Fold `GEvalScorer`'s 3-layer weighted scoring + 3-judge-majority-vote + 4 bias mitigation vào bên trong `AdaptiveJudge` như một scoring strategy cụ thể (không mất năng lực đã có, chỉ đổi entry point).
3. Fold `pedagogical_scorer.py`'s 5-dimension vào `RubricSelector` như một rubric set — không để nó là kênh riêng, tách rời khỏi scoring chính, vì hiện tại điểm pedagogical không ảnh hưởng gì tới pass/fail decision thật.
4. Đánh giá `LiveReviewerQualityGate`: nếu chức năng của nó (deterministic lenses + calibration) trùng lặp với `AdaptiveJudge`, xóa nó. Nếu nó phục vụ mục đích khác thật sự (ví dụ: fast, non-LLM pre-check trước khi gọi `AdaptiveJudge` tốn tiền hơn) — **document rõ ràng vai trò khác biệt** và giữ nó như một layer riêng có tên gọi rõ (ví dụ "Layer 3.5 — Deterministic Pre-Screen"), không để nó mập mờ là "một judge khác".
5. Trước khi cutover hoàn toàn: chạy `AdaptiveJudge` song song với `GEvalScorer` (shadow mode) trên một tập run lịch sử, so sánh pass/fail decision — nếu có phân kỳ đáng kể, điều tra trước khi tắt `GEvalScorer` (an toàn hơn cắt mù, đặc biệt vì hard-block liên quan an toàn học sinh).

## Checklist hành động

- [ ] **Chốt quyết định sản phẩm** về fast-lane vs INVARIANT-06 (Option A/B ở trên) — blocker cho mọi việc khác trong file này
- [ ] Nếu Option A: sửa nội dung + enforcement của INVARIANT-06, đảm bảo audit log phân biệt rõ auto-approve vs manual approve
- [ ] Chạy `AdaptiveJudge` shadow mode song song `GEvalScorer` trên historical runs, so sánh decision parity
- [ ] Fold GEvalScorer's scoring logic + bias mitigations vào AdaptiveJudge
- [ ] Fold `pedagogical_scorer.py` vào RubricSelector
- [ ] Quyết định giữ/xóa `LiveReviewerQualityGate`, document rõ nếu giữ
- [ ] Cutover `reviewer_node` sang gọi `AdaptiveJudge` duy nhất
- [ ] Xóa `GEvalScorer`/`pedagogical_scorer.py` khỏi đường live (giữ code trong `layer4_judge` nếu dùng nội bộ AdaptiveJudge, xóa nếu không)
- [ ] Viết test riêng cho mỗi 1 trong 9 hard-block, chạy qua đúng đường production path (không test qua `AdaptiveJudge` trực tiếp nếu `reviewer_node` không thật sự gọi nó tương tự)
