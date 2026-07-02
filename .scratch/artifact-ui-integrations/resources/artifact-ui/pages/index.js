const { renderPage, writeFile } = require("../render.js");
const { footer } = require("../partials.js");

function card(href, cat, eyebrow, title, desc) {
  return `
  <a href="${href}" class="art-card art-card--rail" style="--card-accent:var(--art-${cat});display:block;text-decoration:none;">
    <span class="art-card-meta art-mono">${eyebrow}</span>
    <div class="art-card-title">${title}</div>
    <p style="margin:0;font-size:13px;color:var(--art-ink-soft)">${desc}</p>
  </a>`;
}

const body = `
<header class="art-cover">
  <p class="art-cover-eyebrow art-mono">oh-my-class · ADR-023</p>
  <h1>ARTIFACT UI</h1>
  <p class="art-cover-sub">Implementation Handoff · Issues 001 · 002 · 003</p>
  <p class="art-cover-copy">Bộ cấu phần lõi + 4 visual family sinh từ 6 template tham chiếu. Mọi trang bên dưới là file HTML độc lập, mở được ngay cả khi không có mạng.</p>
</header>

<main class="art-shell art-shell--wide">

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">Issue 001</span>
      <h2>Core Primitives</h2>
    </div>
    <div style="display:grid;grid-template-columns:1fr;gap:14px;">
      ${card("core-primitives.html", "cat1", "Component showcase", "Core Artifact UI Primitives", "Theme switcher trực tiếp giữa 4 family + toàn bộ cấu phần lõi + 3 trạng thái chẩn đoán.")}
    </div>
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">Issue 002</span>
      <h2>Semantic Vocabulary — navy-ticket family</h2>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
      ${card("semantic-vocabulary/index.html", "cat2", "Batch export", "Batch Index — Unit 2 Travel & Transport", "Manifest ngoại tuyến cho 4 cụm: 2 đạt, 1 cần rà soát, 1 thất bại.")}
      ${card("semantic-vocabulary/cluster-01-travel/teaching.student.html", "cat1", "Passed · Student", "Nhóm 01 — Teaching (Student)", "5 từ chỉ \"chuyến đi\" — bản học sinh, không có kịch bản giảng hay nguồn tham chiếu.")}
      ${card("semantic-vocabulary/cluster-01-travel/teaching.teacher.html", "cat6", "Passed · Teacher", "Nhóm 01 — Teaching (Teacher)", "Bản đầy đủ: kịch bản giảng, nguồn tham chiếu, lưu ý biên soạn.")}
      ${card("semantic-vocabulary/cluster-01-travel/practice.student.html", "cat1", "Passed · Student", "Nhóm 01 — Practice (Student)", "4 câu luyện tập không đáp án.")}
      ${card("semantic-vocabulary/cluster-02-fare/teaching.student.html", "cat2", "Passed · Student", "Nhóm 02 — Teaching (Student)", "3 từ chỉ \"tiền vé\" — bản học sinh.")}
      ${card("semantic-vocabulary/cluster-03-compensate/review.teacher.html", "cat3", "Needs review · Teacher only", "Nhóm 03 — Review Draft", "Cụm chưa đủ nguồn đối chiếu — chỉ xuất file rà soát nội bộ.")}
      ${card("semantic-vocabulary/cluster-04-insufficient-input/diagnostics.html", "cat5", "Failed · Diagnostics only", "Input không đủ dữ liệu", "Không tạo nội dung giảng dạy — chỉ báo cáo chẩn đoán lỗi.")}
    </div>
  </section>

  <section class="art-section" style="margin-bottom:0;">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">Issue 003</span>
      <h2>Specialized Artifact Families</h2>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
      ${card("families/lesson-path.html", "cat1", "paper-dossier", "Lesson / Path Dossier", "Roadmap 4 giai đoạn, objective card, concept box, roleplay script, homework.")}
      ${card("families/exam-key.html", "cat2", "paper-dossier", "Exam Answer Key", "Question grid, option states, giải thích bản chất + bẫy sai cho từng câu.")}
      ${card("families/video-route.html", "cat4", "transit-route", "Video Learning Route", "Ticket header, mini route map, 6 trạm học, video placeholder offline-safe.")}
      ${card("families/inverse-thinking.html", "cat5", "investigation-folder", "Inverse Thinking — Case File", "Hồ sơ điều tra, quy trình loại trừ 4 bước, bằng chứng, kết luận.")}
    </div>
  </section>

  <section class="art-section" style="margin-bottom:0;">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">Issue 004 · 005</span>
      <h2>Root-Cause / Socratic Teaching Primitives</h2>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
      ${card("core-primitives.html#10", "cat3", "Component showcase", "7 cấu phần Socratic mới", "Anchor timeline, controlled comparison (n=2/3/4/6), scenario anchor, checkpoint, stress test, metaphor log, mastery marker — xem mục 10.")}
      ${card("families/root-cause-session.html", "cat1", "paper-dossier", "Root-Cause Session Dossier", "Artifact thật đầu tiên dùng cả 7 cấu phần Issue 004 — buổi dạy Future Perfect vs. Future Perfect Continuous, dựng dưới family Paper Dossier có sẵn.")}
    </div>
  </section>

</main>
${footer("Implementation handoff index", "Xem docs/component-reference.md và HANDOFF.md để biết chi tiết ánh xạ với acceptance criteria từng issue.")}
`;

writeFile("index.html", renderPage({ family: "navy-ticket", title: "Artifact UI — Implementation Handoff", body }));
console.log("top-level index generated.");
