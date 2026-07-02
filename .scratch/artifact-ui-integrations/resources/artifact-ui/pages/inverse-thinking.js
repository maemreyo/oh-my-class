const { renderPage, writeFile } = require("../render.js");
const { footer } = require("../partials.js");

const body = `
<header class="art-cover art-cover--folder">
  <p class="art-cover-eyebrow art-mono">Investigation Folder · Inverse Thinking</p>
  <h1 style="text-align:left;font-size:38px;">Hồ sơ điều tra: "Compensation"</h1>
  <p class="art-cover-sub" style="text-align:left;">Case File #04 · Unit 2 — Travel &amp; Transport</p>
  <div class="art-meta-chips">
    <span class="art-pill">3 nghi phạm</span>
    <span class="art-pill">Độ khó: Trung bình</span>
    <span class="art-pill">15 phút</span>
  </div>
</header>

<main class="art-shell">
  <nav class="art-tabs">
    <button class="art-active">Hồ sơ vụ án</button>
    <button>Quy trình suy luận</button>
    <button>Bằng chứng</button>
    <button>Kết luận</button>
  </nav>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">Vụ án</span>
      <h2>Tình huống</h2>
    </div>
    <div class="art-case">
      <div class="art-case-head"><span class="art-case-tag">Hiện trường</span><span class="art-case-title">"The airline ___ passengers for the delay with meal vouchers."</span></div>
      <p class="art-desc">Ba từ nghi phạm — <b>compensate</b>, <b>reimburse</b>, <b>refund</b> — đều liên quan đến việc "đền bù", nhưng chỉ một từ đúng bản chất câu chuyện này. Học sinh đóng vai thám tử, loại trừ từng nghi phạm bằng bằng chứng ngữ nghĩa.</p>
    </div>
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">Suy luận ngược</span>
      <h2>Quy trình loại trừ</h2>
    </div>
    <div class="art-process-strip">
      <div class="art-pstep art-active"><span class="art-n">01</span><div class="art-t">Đọc kỹ hiện trường</div><div class="art-d">Xác định: đền bù bằng gì? (tiền hay hiện vật?)</div></div>
      <div class="art-pstep"><span class="art-n">02</span><div class="art-t">Loại "refund"</div><div class="art-d">Refund luôn là tiền mặt hoàn lại — ở đây là voucher, không phải tiền.</div></div>
      <div class="art-pstep"><span class="art-n">03</span><div class="art-t">Loại "reimburse"</div><div class="art-d">Reimburse cần hành khách đã chi tiền trước — đề bài không nhắc điều này.</div></div>
      <div class="art-pstep"><span class="art-n">04</span><div class="art-t">Kết tội "compensate"</div><div class="art-d">Chủ động trao giá trị tương đương (voucher) cho thiệt hại (delay) → đúng nghi phạm.</div></div>
    </div>
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">Bằng chứng</span>
      <h2>Exhibit A — Câu gốc</h2>
    </div>
    <div class="art-evidence">
      <span class="art-exhibit-label">Nguồn: Cambridge Dictionary — ví dụ minh hoạ</span>
      <p class="art-exhibit">"Compensate" thường đi kèm giới từ <b>for</b> khi nói về việc đền bù thiệt hại, và đối tượng nhận có thể là người (passengers), không nhất thiết là tiền mặt.</p>
    </div>
  </section>

  <section class="art-section" style="margin-bottom:0;">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">Kết luận</span>
      <h2>Chân dung nghi phạm bị kết tội</h2>
    </div>
    <div class="art-wanted-card" style="max-width:320px;">
      <span class="art-wanted-tag">Đã xác định</span>
      <div class="art-alias">Compensate</div>
      <p style="font-size:12.5px;color:var(--art-ink-soft);margin:0 0 8px;">Chủ động trao giá trị tương đương cho thiệt hại — không nhất thiết là tiền mặt.</p>
      <div class="art-key-row">
        <span class="art-key-chip">+ for</span>
        <span class="art-key-chip">chủ động</span>
        <span class="art-key-chip">giá trị tương đương</span>
      </div>
    </div>
  </section>
</main>
${footer("Investigation Folder showcase · Issue 003")}
`;

writeFile("families/inverse-thinking.html", renderPage({ family: "investigation-folder", title: 'Case File — "Compensation"', body }));
console.log("inverse-thinking family generated.");
