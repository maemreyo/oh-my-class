const { renderPage, writeFile } = require("../render.js");
const { diagnosticsPanel, projectionFlag, teacherBlock, footer } = require("../partials.js");
const { clusters, failedCluster } = require("./semantic-vocabulary-data.js");

const FAMILY = "navy-ticket";

// ---------------------------------------------------------------------
// Practice items (ADR-022 §2 — 4 exercise intents), keyed by cluster id
// ---------------------------------------------------------------------
const practiceByCluster = {
  "cluster-01-travel": [
    {
      intent: "Nhận diện từ khoá cốt lõi",
      prompt: "Nhìn hình ảnh gợi ý \"nhiều điểm dừng, đường dài, mỏi chân\" — đây là ấn tượng của từ nào trong nhóm?",
      options: ["A. Voyage", "B. Journey", "C. Trip", "D. Excursion"],
      answer: "B. Journey",
      rationale: "\"Path / nhiều stop points\" là visual cue riêng của Journey — khác Voyage (quy mô lớn) và Trip (mục đích rõ ràng).",
    },
    {
      intent: "Phân biệt theo ngữ cảnh",
      prompt: "\"He took a two-day business ___ to Da Nang and flew back on Friday.\"",
      options: ["A. voyage", "B. journey", "C. trip", "D. travel"],
      answer: "C. trip",
      rationale: "Có mục đích công việc rõ ràng (business) + quay về đúng chỗ cũ trong thời gian ngắn → đặc trưng của Trip.",
    },
    {
      intent: "Giải thích ranh giới",
      prompt: "Vì sao không thể nói \"a travel to Japan\" mà phải nói \"a trip to Japan\"?",
      answer: "Vì Travel là danh từ không đếm được (uncountable) — chỉ khái niệm vĩ mô, không thể đứng sau mạo từ \"a\".",
      rationale: "Đây là lỗi phổ biến nhất trong cụm — Travel không có dạng số ít \"a travel\" hay số nhiều \"travels\" (chỉ chuyến đi cụ thể).",
    },
    {
      intent: "Truy hồi ngược",
      prompt: "Từ nào trong nhóm luôn gắn với không khí \"vui vẻ, dã ngoại tập thể, có tổ chức\"?",
      answer: "Excursion",
      rationale: "Impression \"Vui vẻ\" + visual cue \"Picnic / dã ngoại\" là đặc trưng riêng, không trùng với 4 từ còn lại trong cụm.",
    },
  ],
  "cluster-02-fare": [
    {
      intent: "Nhận diện từ khoá cốt lõi",
      prompt: "Âm thanh \"tiếng còi xe, tiếng động cơ\" gợi nhớ đến từ nào?",
      options: ["A. Fare", "B. Ticket", "C. Fee"],
      answer: "A. Fare",
      rationale: "Core trigger \"Vehicle\" + visual cue \"Engine / bánh xe lăn\" chỉ gắn với Fare trong cụm này.",
    },
    {
      intent: "Phân biệt theo ngữ cảnh",
      prompt: "\"The museum charges an admission ___ of fifty thousand dong for adults.\"",
      options: ["A. fare", "B. ticket", "C. fee"],
      answer: "C. fee",
      rationale: "Không có phương tiện di chuyển nào ở đây — tiền trả cho quyền vào cửa một tổ chức luôn là Fee.",
    },
    {
      intent: "Giải thích ranh giới",
      prompt: "Fare và Ticket khác nhau ở điểm cốt lõi nào?",
      answer: "Fare là số tiền trừu tượng bạn trả; Ticket là vật thể cụ thể (giấy/thẻ/QR) bạn nhận lại sau khi trả Fare.",
      rationale: "Học sinh hay dùng lẫn hai từ vì cùng xuất hiện trong ngữ cảnh đi xe — nhấn: một cái là tiền, một cái là vật.",
    },
  ],
};

function renderTicket(t, isTeacher) {
  return `
  <article class="art-ticket art-avoid-break">
    <div class="art-ticket-main">
      <h3 class="art-ticket-word">${t.word}</h3>
      <p class="art-ticket-desc">${t.studentExplanation}</p>
      <p class="art-semantic-chain">${t.word} <span class="art-arrow">→</span> <b>${t.impression}, ${t.coreTrigger.toLowerCase()}</b> <span class="art-arrow">→</span> ${t.coreTrigger} <span class="art-arrow">→</span> ${t.visualCue}</p>
      <p style="font-size:13px;color:var(--art-ink-soft);margin:0 0 10px;"><b style="color:var(--art-ink)">Ví dụ:</b> <em>${t.example}</em></p>
      <div class="art-contrast-quote"><span class="art-who">Ranh giới</span>${t.contrastNote}</div>
      ${
        isTeacher
          ? teacherBlock(
              "Kịch bản giảng (dùng nguyên văn trên lớp)",
              `<p class="art-teacher-script"><span class="art-script-line">${t.teacherScript}</span></p>
               <p style="font-size:12px;color:var(--art-ink-faint);margin-top:10px;"><b>Nguồn:</b> ${t.sourceNotes}</p>
               <p style="font-size:12px;color:var(--art-ink-faint);margin-top:4px;"><b>Lưu ý:</b> ${t.edgeCases}</p>`
            )
          : ""
      }
    </div>
    <div class="art-ticket-stub">
      <svg class="art-anchor-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="2.2"/><line x1="12" y1="7.2" x2="12" y2="21"/><path d="M5 13a7 7 0 0 0 14 0"/><line x1="5" y1="13" x2="8" y2="13"/><line x1="19" y1="13" x2="16" y2="13"/></svg>
      <span class="art-stub-label">Ấn tượng</span>
      <span class="art-stub-badge">${t.impression}</span>
    </div>
  </article>`;
}

function teachingBody(cluster, isTeacher) {
  return `
${isTeacher ? projectionFlag("Bản dành cho giáo viên — chứa kịch bản giảng &amp; nguồn tham chiếu, không xuất cho học sinh") : ""}
<header class="art-cover">
  <p class="art-cover-eyebrow art-mono">Semantic Anchor Cluster · ${cluster.groupLabel}</p>
  <h1>${cluster.title}</h1>
  <p class="art-cover-sub">${isTeacher ? "Teaching Guide · Teacher Edition" : "Teaching Guide · Student Edition"}</p>
  <p class="art-cover-copy">${cluster.subtitle}</p>
  <div class="art-cover-pills">
    <span class="art-pill">${cluster.terms.length} từ trong cụm</span>
    <span class="art-pill">Unit 2 · Travel &amp; Transport</span>
  </div>
</header>
<main class="art-shell">
  <div class="art-callout art-callout--dashed" style="margin-bottom:32px;">
    <span class="art-glyph art-mono">i</span>
    <span>Mỗi từ có một "ấn tượng" và một chuỗi liên tưởng riêng — dạy đúng thứ tự Word → Impression → Core trigger → Visual cue để học sinh ghi nhớ theo neo ngữ nghĩa, không học vẹt nghĩa tiếng Việt.</span>
  </div>
  ${cluster.terms.map((t) => renderTicket(t, isTeacher)).join("\n")}
</main>
${footer(
  isTeacher ? "Teaching Guide — Teacher" : "Teaching Guide — Student",
  isTeacher
    ? "Tài liệu nội bộ giáo viên. Không chia sẻ trực tiếp cho học sinh hoặc đăng lên nhóm lớp công khai."
    : "Tài liệu học tập cho học sinh — có thể in hoặc chia sẻ tự do."
)}
`;
}

function practiceBody(cluster, isTeacher) {
  const items = practiceByCluster[cluster.id] || [];
  return `
${isTeacher ? projectionFlag("Bản dành cho giáo viên — chứa đáp án &amp; giải thích, không xuất cho học sinh") : ""}
<div class="art-page-head">
  <p class="art-cover-eyebrow art-mono">Semantic Anchor Cluster · ${cluster.groupLabel}</p>
  <h1>Luyện tập — ${cluster.title}</h1>
  <p class="art-lede">${items.length} câu theo 4 dạng: nhận diện từ khoá cốt lõi, phân biệt theo ngữ cảnh, giải thích ranh giới, truy hồi ngược.</p>
</div>
<main class="art-shell">
  ${items
    .map(
      (it, i) => `
  <div class="art-practice-item art-avoid-break">
    <p class="art-pq-text"><span class="art-pq-n">Câu ${i + 1} · ${it.intent}</span><br>${it.prompt}</p>
    ${it.options ? `<div class="art-pq-opts">${it.options.map((o) => `<span>${o}</span>`).join("")}</div>` : ""}
    ${
      isTeacher
        ? `<div class="art-pq-ans">Đáp án: ${it.answer}</div><div class="art-pq-why">${it.rationale}</div>`
        : ""
    }
  </div>`
    )
    .join("\n")}
</main>
${footer(
  isTeacher ? "Practice Set — Teacher" : "Practice Set — Student",
  isTeacher
    ? "Bao gồm đáp án và giải thích — dùng để chấm hoặc chữa bài trên lớp."
    : "Không có đáp án trong file này — dùng để học sinh tự làm trước khi chữa bài."
)}
`;
}

function reviewBody(cluster) {
  return `
${projectionFlag("Bản rà soát cho giáo viên — CHƯA xuất bản cho học sinh hoặc LMS")}
<div class="art-page-head">
  <p class="art-cover-eyebrow art-mono">Semantic Anchor Cluster · ${cluster.groupLabel} · Cần rà soát</p>
  <h1>${cluster.title}</h1>
  <p class="art-lede">${cluster.subtitle}</p>
</div>
<main class="art-shell">
  ${diagnosticsPanel({
    status: "needs_review",
    title: "Lý do cần rà soát",
    rows: [
      { k: "Lý do", v: cluster.reviewReason },
      { k: "Đề xuất", v: cluster.reviewSuggestion },
      { k: "Parse confidence", v: cluster.parseConfidence },
    ],
  })}
  <div style="height:32px"></div>
  <div class="art-callout" style="margin-bottom:24px;">
    <span class="art-glyph art-mono">!</span>
    <span>Nội dung bên dưới là bản nháp đầy đủ nhất hiện có — giáo viên xác nhận rồi mới cho chạy lại batch để xuất bản teaching + practice chính thức.</span>
  </div>
  ${cluster.terms.map((t) => renderTicket(t, true)).join("\n")}
</main>
${footer("Review draft — Teacher only", "File này chỉ dùng nội bộ để giáo viên xác nhận nội dung trước khi duyệt xuất bản.")}
`;
}

function diagnosticsOnlyBody(fc) {
  return `
${projectionFlag("Báo cáo chẩn đoán — không có nội dung giảng dạy nào được tạo ra")}
<div class="art-page-head">
  <p class="art-cover-eyebrow art-mono">Semantic Anchor Cluster · Thất bại</p>
  <h1>Không đủ dữ liệu để tạo cụm</h1>
  <p class="art-lede">Input dưới ngưỡng xử lý tối thiểu — hệ thống dừng lại và báo cáo thay vì đoán nội dung.</p>
</div>
<main class="art-shell">
  ${diagnosticsPanel({
    status: "failed",
    title: "Chi tiết lỗi",
    rows: [
      { k: "Đoạn input gốc", v: fc.rawInputSpan },
      { k: "Lý do thất bại", v: fc.reason },
      { k: "Parse confidence", v: fc.parseConfidence },
      { k: "Đề xuất", v: fc.suggestion },
    ],
  })}
</main>
${footer("Diagnostics only", "Không có nội dung giảng dạy nào được sinh ra cho input này.")}
`;
}

// ---------------------------------------------------------------------
// Generate files
// ---------------------------------------------------------------------
for (const cluster of clusters.filter((c) => c.status === "passed")) {
  writeFile(
    `semantic-vocabulary/${cluster.id}/teaching.teacher.html`,
    renderPage({
      family: FAMILY,
      title: `${cluster.title} — Teaching (Teacher)`,
      body: teachingBody(cluster, true),
    })
  );
  writeFile(
    `semantic-vocabulary/${cluster.id}/teaching.student.html`,
    renderPage({
      family: FAMILY,
      title: `${cluster.title} — Teaching (Student)`,
      body: teachingBody(cluster, false),
    })
  );
  writeFile(
    `semantic-vocabulary/${cluster.id}/practice.teacher.html`,
    renderPage({
      family: FAMILY,
      title: `${cluster.title} — Practice (Teacher)`,
      body: practiceBody(cluster, true),
    })
  );
  writeFile(
    `semantic-vocabulary/${cluster.id}/practice.student.html`,
    renderPage({
      family: FAMILY,
      title: `${cluster.title} — Practice (Student)`,
      body: practiceBody(cluster, false),
    })
  );
}

for (const cluster of clusters.filter((c) => c.status === "needs_review")) {
  writeFile(
    `semantic-vocabulary/${cluster.id}/review.teacher.html`,
    renderPage({
      family: FAMILY,
      title: `${cluster.title} — Needs Review (Teacher)`,
      body: reviewBody(cluster),
    })
  );
}

writeFile(
  `semantic-vocabulary/${failedCluster.id}/diagnostics.html`,
  renderPage({
    family: FAMILY,
    title: "Cluster failed — Diagnostics",
    body: diagnosticsOnlyBody(failedCluster),
  })
);

// ---------------------------------------------------------------------
// Batch index / manifest (ADR-021 §7)
// ---------------------------------------------------------------------
const rows = [];
for (const c of clusters) {
  if (c.status === "passed") {
    rows.push({ cluster: c.title, group: c.groupLabel, status: "passed", files: [
      `${c.id}/teaching.teacher.html`, `${c.id}/teaching.student.html`,
      `${c.id}/practice.teacher.html`, `${c.id}/practice.student.html`,
    ]});
  } else if (c.status === "needs_review") {
    rows.push({ cluster: c.title, group: c.groupLabel, status: "needs_review", files: [`${c.id}/review.teacher.html`] });
  }
}
rows.push({ cluster: "Input không đủ (historic...)", group: "—", status: "failed", files: [`${failedCluster.id}/diagnostics.html`] });

const statusTag = (s) =>
  s === "passed" ? `<span class="art-tag art-tag--positive">Đạt</span>` :
  s === "needs_review" ? `<span class="art-tag art-tag--caution">Cần rà soát</span>` :
  `<span class="art-tag art-tag--critical">Thất bại</span>`;

const indexBody = `
<header class="art-cover">
  <p class="art-cover-eyebrow art-mono">Batch export · Vocabulary Pipeline</p>
  <h1>Unit 2 — Travel &amp; Transport</h1>
  <p class="art-cover-sub">Semantic Anchor Batch · ${rows.length} cụm được xử lý</p>
  <p class="art-cover-copy">Chỉ mục ngoại tuyến cho toàn bộ output của batch này. Mở trực tiếp file HTML tương ứng — không cần server hay kết nối mạng.</p>
</header>
<main class="art-shell art-shell--wide">
  <div class="art-stat-grid" style="margin-bottom:40px;">
    <div class="art-stat-card"><div class="art-k">Tổng số cụm</div><div class="art-v">${rows.length}</div></div>
    <div class="art-stat-card"><div class="art-k">Đạt</div><div class="art-v">${clusters.filter((c) => c.status === "passed").length}</div></div>
    <div class="art-stat-card"><div class="art-k">Cần rà soát</div><div class="art-v">${clusters.filter((c) => c.status === "needs_review").length}</div></div>
    <div class="art-stat-card"><div class="art-k">Thất bại</div><div class="art-v">1</div></div>
  </div>

  <div class="art-table-wrap art-avoid-break">
    <div class="art-table-head"><strong>Manifest</strong><span class="art-mono">batch-2026-07-02</span></div>
    <table class="art-table">
      <thead><tr><th>Cụm</th><th>Nhóm</th><th>Trạng thái</th><th>File</th></tr></thead>
      <tbody>
        ${rows
          .map(
            (r) => `<tr>
              <td class="art-strong">${r.cluster}</td>
              <td class="art-mono-cell">${r.group}</td>
              <td>${statusTag(r.status)}</td>
              <td>${r.files.map((f) => `<a href="${f}">${f.split("/").pop()}</a>`).join("<br>")}</td>
            </tr>`
          )
          .join("\n")}
      </tbody>
    </table>
  </div>
</main>
${footer("Batch manifest", "Mọi liên kết trong bảng đều là đường dẫn tương đối cùng thư mục — hoạt động khi mở offline hoặc giải nén từ ZIP.")}
`;

writeFile(
  "semantic-vocabulary/index.html",
  renderPage({ family: FAMILY, title: "Unit 2 — Batch Export Index", body: indexBody })
);

console.log("semantic-vocabulary batch generated.");
