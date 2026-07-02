// Issue 005 — first real end-to-end artifact built on Issue 004's
// primitives: one Root-Cause / Socratic Session dossier, under the
// existing Paper Dossier family (§10.5's default), not a new 5th family.
// Single continuous scroll — `.art-shell`, not `.art-shell--split` — a
// session has no persistent multi-week sidebar to pin.

const { renderPage, writeFile, INTERACTIVITY_JS } = require("../render.js");
const {
  footer,
  renderScenarioAnchor,
  renderAnchorTimeline,
  renderControlledComparison,
  renderMasteryMarker,
  renderGeneralizationCheckpoint,
  renderStressTest,
  renderMetaphorLog,
  renderExceptionReveal,
} = require("../partials.js");
const {
  scenario,
  futurePerfectTimeline,
  futurePerfectContinuousTimeline,
  fourTenseComparison,
  masteryMarkers,
  closingPrompt,
  illustrativeExceptionReveal,
  illustrativeCheckpoint,
  illustrativeStressTest,
  illustrativeMetaphorLog,
} = require("./root-cause-session-data.js");

function illustrativeNote(text) {
  return `<p class="art-illustrative-note art-mono">${text}</p>`;
}

const body = `
<header class="art-page-head">
  <p class="art-cover-eyebrow art-mono">Root-Cause / Socratic Session · Issue 005</p>
  <h1 style="margin:0 0 8px;">Future Perfect vs. Future Perfect Continuous</h1>
  <p class="art-lede">Một buổi dạy 1-kèm-1 theo <span class="art-mono">rooted-in-strength-learning</span> — Zamery, đi từ một tình huống cụ thể, giữ nguyên một mốc, chỉ đổi khía cạnh của thì. Đây là bản ghi lại một phiên thật, không phải giáo trình biên soạn trước.</p>
</header>

<main class="art-shell">

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">01</span>
      <h2>Tình huống mở đầu</h2>
    </div>
    ${renderScenarioAnchor({ scenario })}
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">02</span>
      <h2>Đứng tại mốc, nhìn ngược lại — 2 cách nhìn</h2>
      <p class="art-section-sub">Cùng một mốc (9h tối mai, mèo chạy qua sân) — Rule #11: giữ nguyên kịch bản gốc, chỉ đổi đúng 1 biến (khía cạnh của thì) để thấy rõ tác động của riêng biến đó.</p>
    </div>
    ${renderAnchorTimeline(futurePerfectTimeline)}
    ${renderAnchorTimeline(futurePerfectContinuousTimeline)}
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">03</span>
      <h2>Học sinh tự đề xuất cách hiểu — chờ xác nhận</h2>
    </div>
    ${illustrativeNote("Minh hoạ, không phải từ buổi học thật — transcript gốc dừng lại trước khi Zamery tự đề xuất cách hiểu của mình.")}
    ${renderGeneralizationCheckpoint(illustrativeCheckpoint)}
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">04</span>
      <h2>Trường hợp ngoại lệ của cách hiểu vừa chỉnh</h2>
      <p class="art-section-sub">Rule #7: chỉ mở ngoại lệ SAU khi quy tắc gốc đã landed ở mục 02 — không đẩy lên trước.</p>
    </div>
    ${illustrativeNote("Minh hoạ, không phải từ buổi học thật — transcript gốc dừng lại trước khi Zamery chạm tới trường hợp ngoại lệ này.")}
    ${renderExceptionReveal(illustrativeExceptionReveal)}
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">05</span>
      <h2>Học sinh tự bẻ luật để kiểm chứng</h2>
    </div>
    ${illustrativeNote("Minh hoạ, không phải từ buổi học thật — transcript gốc dừng lại trước khi Zamery tự dựng một câu sai để test giới hạn quy tắc.")}
    ${renderStressTest(illustrativeStressTest)}
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">06</span>
      <h2>Ẩn dụ đã thử — cái nào trúng</h2>
    </div>
    ${illustrativeNote("Minh hoạ, không phải từ buổi học thật — transcript gốc chỉ dùng đúng 1 ẩn dụ ngay từ đầu, không có lần thử hụt nào được ghi lại.")}
    ${renderMetaphorLog(illustrativeMetaphorLog)}
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">07</span>
      <h2>Tóm lại — mặt cắt tư duy của cả 4 thì</h2>
      <p class="art-section-sub">Nguyên văn phần chốt của buổi học: giữ nguyên kịch bản, chỉ đổi khía cạnh thì tương lai được đánh dấu.</p>
    </div>
    ${renderControlledComparison(fourTenseComparison)}
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">08</span>
      <h2>Trạng thái nắm vững</h2>
      <p class="art-section-sub">Buổi học kết thúc bằng lời mời áp dụng sang tình huống mới, không phải một tín hiệu "chốt xong" — cả 2 khái niệm vẫn ở trạng thái "mở", không tự gán "đã hiểu".</p>
    </div>
    <div style="display:flex; gap:12px; flex-wrap:wrap;">
      ${masteryMarkers.map((m) => renderMasteryMarker(m)).join("\n")}
    </div>
  </section>

  <section class="art-section" style="margin-bottom:0;">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">09</span>
      <h2>Lời mời áp dụng tiếp</h2>
    </div>
    <div class="art-callout">
      <span class="art-glyph art-mono">→</span>
      <span>${closingPrompt}</span>
    </div>
  </section>

</main>
${footer(
  "Root-cause session dossier · Issue 005",
  "Bản ghi một phiên dạy 1-kèm-1 thật, dựng bằng các cấu phần Issue 004 dưới family Paper Dossier có sẵn — không phải một family mới.",
)}
`;

const extraCss = `
/* Page-specific only: small illustrative-content flag, not a reusable primitive */
.art-illustrative-note {
  display: inline-block;
  font-size: 10.5px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--art-ink-faint);
  background: var(--art-surface-muted);
  border: 1px dashed var(--art-border-strong);
  border-radius: var(--art-radius-pill);
  padding: 4px 12px;
  margin-bottom: var(--art-space-3);
}
`;

const html = renderPage({
  family: "paper-dossier",
  title: "Root-Cause Session — Future Perfect vs. Future Perfect Continuous",
  body,
  extraCss,
  script: INTERACTIVITY_JS,
});

const out = writeFile("families/root-cause-session.html", html);
console.log("wrote", out);
