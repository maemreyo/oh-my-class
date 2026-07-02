const { renderMultiThemePage, writeFile } = require("../render.js");
const { diagnosticsPanel, projectionFlag, teacherBlock, footer } = require("../partials.js");

const signatureByFamily = {
  "navy-ticket": `
  <article class="art-ticket art-avoid-break">
    <div class="art-ticket-main">
      <h3 class="art-ticket-word">Voyage</h3>
      <p class="art-ticket-desc">Chuyến đi mang tính lịch sử — vượt đại dương hoặc lao vào vũ trụ. Không dành cho một buổi dạo chơi ngắm cảnh thông thường.</p>
      <p class="art-semantic-chain">Voyage <span class="art-arrow">→</span> <b>Hoành tráng, dài ngày</b> <span class="art-arrow">→</span> Explore <span class="art-arrow">→</span> tàu thủy lớn / phi thuyền</p>
      <div class="art-contrast-quote"><span class="art-who">Cách giảng</span>"Nói đến Voyage là nói đến Columbus khám phá châu Mỹ."</div>
    </div>
    <div class="art-ticket-stub">
      <svg class="art-anchor-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="2.2"/><line x1="12" y1="7.2" x2="12" y2="21"/><path d="M5 13a7 7 0 0 0 14 0"/><line x1="5" y1="13" x2="8" y2="13"/><line x1="19" y1="13" x2="16" y2="13"/></svg>
      <span class="art-stub-label">Ấn tượng</span>
      <span class="art-stub-badge">Hoành tráng</span>
    </div>
  </article>`,
  "paper-dossier": `
  <div class="art-phase-rail art-avoid-break">
    <div class="art-phase-block" style="--phase-color:var(--art-cat-1)">
      <span class="art-phase-dot" style="--phase-color:var(--art-cat-1)"></span>
      <div class="art-phase-card">
        <div class="art-phase-top"><span class="art-phase-when" style="--phase-color:var(--art-cat-1)">Giai đoạn 1 · Tuần 1–4</span></div>
        <div class="art-phase-goal">Xây nền từ vựng đối chiếu + phrasal verbs theo unit.</div>
        <div class="art-phase-output">Đầu ra: 6 buổi vocab, mỗi buổi 1 bản đồ đối chiếu + roleplay.</div>
      </div>
    </div>
  </div>`,
  "transit-route": `
  <div class="art-station art-avoid-break">
    <div class="art-station-rail"><span class="art-dot" style="--st-color:var(--art-cat-2)"></span><span class="art-thread"></span></div>
    <div class="art-station-body art-cat2" style="--st-color:var(--art-cat-2)">
      <div class="art-station-head"><span class="art-station-code">GA02</span><span class="art-station-title">Nghe lần 1 — Bắt ý chính</span></div>
      <p class="art-station-sub">Nghe toàn bài 1 lượt, chỉ ghi lại chủ đề &amp; số người nói.</p>
    </div>
  </div>`,
  "investigation-folder": `
  <div class="art-case art-avoid-break">
    <div class="art-case-head"><span class="art-case-tag">Hồ sơ 04</span><span class="art-case-title">Nghi phạm: "Compensation"</span></div>
    <p class="art-desc">Ba phương án gây nhiễu đều <b>gần giống</b> nghĩa nhưng sai bản chất — học sinh cần loại trừ từng nghi phạm bằng bằng chứng trong câu.</p>
  </div>`,
};

const body = `
<header class="art-cover">
  <p class="art-cover-eyebrow art-mono">Component showcase · Issue 001</p>
  <h1>ARTIFACT UI</h1>
  <p class="art-cover-sub">Core Primitives · Standalone · Offline · Print-safe</p>
  <p class="art-cover-copy">Đây là kho cấu phần lõi dùng chung cho mọi loại artifact được sinh ra — từ thẻ từ vựng đến đề thi. Dùng nút bên trên để đổi visual family và xem cùng một cấu trúc HTML tự thay đổi hoàn toàn diện mạo, chỉ nhờ đổi bộ token.</p>
  <div class="art-cover-pills">
    <span class="art-pill">navy-ticket</span>
    <span class="art-pill">paper-dossier</span>
    <span class="art-pill">transit-route</span>
    <span class="art-pill">investigation-folder</span>
  </div>
</header>

<main class="art-shell art-shell--wide">

  <div class="art-callout art-callout--dashed" style="margin-bottom:56px;">
    <span class="art-glyph art-mono">i</span>
    <span>Trang này là <b>công cụ QA/dev</b>, không phải artifact xuất cho giáo viên hay học sinh. Nó gộp cả 4 bộ token vào một tài liệu để demo cơ chế theme-switch — điều mà một artifact thật <b>không bao giờ làm</b> (mỗi artifact chỉ tải đúng 1 family). Xem <span class="art-mono">docs/component-reference.md</span> để biết quy tắc build thật.</span>
  </div>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">01</span>
      <h2>Sidebar &amp; route navigation</h2>
      <p class="art-section-sub">Hai biến thể điều hướng: danh sách dọc (dossier) và tuyến ngang (route).</p>
    </div>
    <div class="demo-grid demo-grid--sidebar">
      <div style="background:var(--art-surface);border:1px solid var(--art-border);border-radius:var(--art-radius-md);padding:18px;">
        <div class="art-nav-brand"><span class="art-nav-dot">O</span> oh-my-class</div>
        <div class="art-nav-title">Unit 2 — Travel &amp; Transport</div>
        <div class="art-nav-sub">Buổi vocab đầu tiên · Destination B2</div>
        <nav class="art-nav-list">
          <a href="#" class="is-active"><span class="art-nn">1</span> Khởi động — phim</a>
          <a href="#"><span class="art-nn">2</span> Bản đồ đối chiếu</a>
          <a href="#"><span class="art-nn">3</span> Luyện tập hướng dẫn</a>
          <a href="#"><span class="art-nn">4</span> Quiz theo format thi</a>
        </nav>
      </div>
      <div style="background:var(--art-surface);border:1px solid var(--art-border);border-radius:var(--art-radius-md);padding:18px;display:flex;align-items:center;">
        <nav class="art-route-nav" style="border-bottom:none;width:100%;">
          <span class="art-stop is-active"><span class="art-dot"></span>GA01</span>
          <span class="art-track"></span>
          <span class="art-stop"><span class="art-dot"></span>GA02</span>
          <span class="art-track"></span>
          <span class="art-stop"><span class="art-dot"></span>GA03</span>
          <span class="art-track"></span>
          <span class="art-stop"><span class="art-dot"></span>GA04</span>
        </nav>
      </div>
    </div>
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">02</span>
      <h2>Section header + stat cards</h2>
      <span class="art-time-chip">~15 phút</span>
    </div>
    <div class="art-stat-grid">
      <div class="art-stat-card"><div class="art-k">Cụm từ vựng</div><div class="art-v">18 <small>trong batch</small></div></div>
      <div class="art-stat-card"><div class="art-k">Trạng thái</div><div class="art-v">15 <small>đạt / 3 cần rà soát</small></div></div>
      <div class="art-stat-card"><div class="art-k">Nguồn tham chiếu</div><div class="art-v">5+ <small>mỗi cụm</small></div></div>
      <div class="art-stat-card"><div class="art-k">Điểm chất lượng TB</div><div class="art-v">8.4 <small>/ 10</small></div></div>
    </div>
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">03</span>
      <h2>Callout / note box</h2>
    </div>
    <div class="demo-grid demo-grid--2">
      <div class="art-callout"><span class="art-glyph art-mono">!</span><span>Cụm <b>arrive / reach / enter</b> lặp lại lỗi gốc ở câu 2 bài kiểm tra đầu vào — dạy lại đúng điểm này trước tiên.</span></div>
      <div class="art-callout art-callout--dashed"><span class="art-glyph art-mono">i</span><span>Callout biến thể viền chấm — dùng khi đặt trực tiếp lên nền trang thay vì trên thẻ.</span></div>
    </div>
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">04</span>
      <h2>Content card với accent rail</h2>
    </div>
    <div class="demo-grid demo-grid--3">
      <div class="art-card art-card--rail" style="--card-accent:var(--art-cat-1)">
        <span class="art-card-meta art-mono">Ngữ pháp</span>
        <div class="art-card-title">Thì hiện tại hoàn thành</div>
        <p style="margin:0;font-size:13px;color:var(--art-ink-soft)">Dùng cho hành động bắt đầu trong quá khứ, còn ảnh hưởng đến hiện tại.</p>
      </div>
      <div class="art-card art-card--rail" style="--card-accent:var(--art-cat-2)">
        <span class="art-card-meta art-mono">Hội thoại</span>
        <div class="art-card-title">Roleplay sân bay</div>
        <p style="margin:0;font-size:13px;color:var(--art-ink-soft)">Script sẵn lời — học sinh chỉ cần điền vào chỗ trống.</p>
      </div>
      <div class="art-card art-card--rail" style="--card-accent:var(--art-cat-4)">
        <span class="art-card-meta art-mono">Đọc hiểu</span>
        <div class="art-card-title">Điền từ theo ngữ cảnh</div>
        <p style="margin:0;font-size:13px;color:var(--art-ink-soft)">5 chỗ trống, mỗi chỗ có 2 phương án gây nhiễu gần nghĩa.</p>
      </div>
    </div>
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">05</span>
      <h2>Table / comparison matrix</h2>
      <p class="art-section-sub">Ví dụ: so sánh định dạng xuất bài tập (AGENTS.md §10).</p>
    </div>
    <div class="art-table-wrap art-avoid-break">
      <div class="art-table-head"><strong>So sánh định dạng xuất</strong><span class="art-mono">4 định dạng</span></div>
      <table class="art-table">
        <thead><tr><th>Định dạng</th><th>Điểm cộng</th><th class="art-hide-mobile">Hạn chế</th></tr></thead>
        <tbody>
          <tr><td class="art-strong">Moodle GIFT</td><td>Đơn giản, dòng lệnh, dễ implement nhất</td><td class="art-hide-mobile art-mono-cell">Giới hạn kiểu câu hỏi</td></tr>
          <tr><td class="art-strong">H5P</td><td class="art-accented">Tương tác phong phú nhất</td><td class="art-hide-mobile art-mono-cell">Cần thư viện H5P dựng sẵn</td></tr>
          <tr><td class="art-strong">QTI 2.1</td><td>Chuẩn liên thông LMS rộng nhất</td><td class="art-hide-mobile art-mono-cell">Chỉ xuất, không nhập</td></tr>
          <tr><td class="art-strong">Google Forms</td><td>Dễ chia sẻ, quen thuộc với PHHS</td><td class="art-hide-mobile art-mono-cell">Không chấm điểm 1 phần, không LaTeX</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">06</span>
      <h2>Tag / stamp / badge</h2>
    </div>
    <div class="art-chiplist" style="margin-bottom:16px;">
      <span class="art-tag art-tag--cat1">Ngữ pháp</span>
      <span class="art-tag art-tag--cat2">Hội thoại</span>
      <span class="art-tag art-tag--cat3">Viết lại câu</span>
      <span class="art-tag art-tag--cat4">Đọc hiểu</span>
      <span class="art-tag art-tag--cat5">Tư duy logic</span>
      <span class="art-tag art-tag--positive">Đạt</span>
      <span class="art-tag art-tag--caution">Cần rà soát</span>
      <span class="art-tag art-tag--critical">Thất bại</span>
    </div>
    <div style="display:flex;gap:20px;flex-wrap:wrap;">
      <div class="art-stamp art-stamp--positive">ĐÃ<br>DUYỆT</div>
      <div class="art-stamp art-stamp--caution">CẦN<br>RÀ SOÁT</div>
      <div class="art-stamp art-stamp--critical">KHÔNG<br>ĐẠT</div>
    </div>
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">07</span>
      <h2>Diagnostics / review-state panel</h2>
      <p class="art-section-sub">3 trạng thái bắt buộc theo ADR-021: passed · needs_review · failed.</p>
    </div>
    <div style="display:grid;gap:14px;">
      ${diagnosticsPanel({
        status: "passed",
        title: "Cụm #12 — travel / journey / trip / voyage / excursion",
        rows: [
          { k: "Nguồn đối chiếu", v: "6 nguồn từ điển, đối chiếu chéo đạt ngưỡng standard" },
          { k: "Điểm G-Eval", v: "8.7 / 10 — vượt ngưỡng 7.0" },
          { k: "Xuất bản", v: "teaching.teacher.html · teaching.student.html · practice (GIFT, H5P)" },
        ],
      })}
      ${diagnosticsPanel({
        status: "needs_review",
        title: "Cụm #05 — compensate / reimburse / refund",
        rows: [
          { k: "Lý do", v: "Chỉ tìm được 1 nguồn đáng tin cho sắc thái \"refund\" — dưới ngưỡng 2 nguồn tối thiểu" },
          { k: "Đề xuất", v: "Giáo viên xác nhận ví dụ trước khi xuất cho học sinh" },
          { k: "Xuất bản", v: "Chỉ file rà soát cho giáo viên — chưa xuất học sinh/LMS" },
        ],
      })}
      ${diagnosticsPanel({
        status: "failed",
        title: "Cụm #19 — input không đủ để phân cụm",
        rows: [
          { k: "Lỗi", v: "parse_confidence thấp — 1 từ duy nhất, không đủ ngữ cảnh để tạo neo ngữ nghĩa" },
          { k: "Xuất bản", v: "Chỉ báo cáo chẩn đoán, không tạo nội dung giảng dạy" },
        ],
      })}
    </div>
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">08</span>
      <h2>Teacher-only / student-safe projection</h2>
      <p class="art-section-sub">Minh hoạ trực quan — bản build thật tách thành 2 file riêng (xem Semantic Vocabulary showcase).</p>
    </div>
    ${projectionFlag("Bản dành cho giáo viên — không xuất cho học sinh")}
    ${teacherBlock(
      "Kịch bản giảng &amp; ghi chú nguồn",
      `<p class="art-teacher-script"><span class="art-script-line">"Nói đến Voyage là nói đến Columbus khám phá châu Mỹ — nó phải có mùi vị của sự hoành tráng."</span></p>
       <p style="font-size:12.5px;color:var(--art-ink-faint);margin-top:8px;">Nguồn: Cambridge Dictionary, Oxford Collocations Dictionary. Ghi chú: học sinh B1 dễ nhầm với "trip" khi không có ngữ cảnh quy mô.</p>`
    )}
  </section>

  <section class="art-section" style="margin-bottom:0;">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">09</span>
      <h2>Signature component theo family đang chọn</h2>
      <p class="art-section-sub">Mỗi family có ít nhất 1 cấu phần đặc trưng riêng — đổi theme ở trên để xem.</p>
    </div>
    <div data-only-theme="navy-ticket">${signatureByFamily["navy-ticket"]}</div>
    <div data-only-theme="paper-dossier">${signatureByFamily["paper-dossier"]}</div>
    <div data-only-theme="transit-route">${signatureByFamily["transit-route"]}</div>
    <div data-only-theme="investigation-folder">${signatureByFamily["investigation-folder"]}</div>
  </section>

</main>
${footer("Core primitives showcase · Issue 001", "Mẫu này minh hoạ toàn bộ cấu phần lõi dùng chung cho 4 visual family. Không dùng trực tiếp làm artifact xuất cho giáo viên/học sinh.")}
`;

const extraCss = `
/* Showcase-only layout utilities (not part of the reusable primitive set) */
.demo-grid { display: grid; gap: 14px; }
.demo-grid--2 { grid-template-columns: 1fr 1fr; }
.demo-grid--3 { grid-template-columns: 1fr 1fr 1fr; }
.demo-grid--sidebar { grid-template-columns: 260px 1fr; }
@media (max-width: 700px) {
  .demo-grid--2, .demo-grid--3, .demo-grid--sidebar { grid-template-columns: 1fr; }
}
`;

const html = renderMultiThemePage({
  title: "Artifact UI — Core Primitives Showcase",
  defaultFamily: "navy-ticket",
  extraCss,
  body,
});

const out = writeFile("core-primitives.html", html);
console.log("wrote", out);
