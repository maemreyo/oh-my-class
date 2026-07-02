const { renderPage, writeFile } = require("../render.js");
const { footer } = require("../partials.js");

const stations = [
  { code: "GA01", cat: "cat1", title: "Khởi động — Đoán chủ đề", sub: "Xem 15 giây đầu (tắt tiếng) — đoán chủ đề video nói về gì.",
    body: `<div class="art-cue-card"><b>Gợi ý:</b> Chú ý trang phục và bối cảnh trong khung hình đầu tiên.</div>` },
  { code: "GA02", cat: "cat2", title: "Nghe lần 1 — Bắt ý chính", sub: "Nghe toàn bài 1 lượt, chỉ ghi lại chủ đề &amp; số người nói.",
    body: `<div class="art-cue-card">Không tua lại, không dừng — nghe trôi hết 1 lượt để luyện phản xạ.</div>` },
  { code: "GA03", cat: "cat3", title: "Nghe lần 2 — Bắt chi tiết", sub: "Nghe lại đoạn 0:45–1:30, điền 3 từ khoá còn thiếu vào phiếu.",
    body: `<div class="art-cue-card">Từ khoá liên quan đến cụm <b>fare / ticket / fee</b> đã học ở Nhóm 02.</div>` },
  { code: "GA04", cat: "cat4", title: "Từ vựng — Chọn lọc theo cụm", sub: "Gạch chân mọi từ thuộc nhóm \"chuyến đi\" xuất hiện trong transcript.",
    body: `<div class="art-cue-card">Transcript đầy đủ nằm ở tài liệu đính kèm — không hiển thị trong artifact này.</div>` },
  { code: "GA05", cat: "cat5", title: "Viết — Tóm tắt 3 câu", sub: "Viết lại nội dung video bằng 3 câu, dùng ít nhất 2 từ vựng vừa học.",
    body: `<div class="art-cue-card">Tự chấm theo rubric: đúng ý (40%) · đúng từ vựng (40%) · đúng ngữ pháp (20%).</div>` },
  { code: "GA06", cat: "cat6", title: "Nói — Kể lại cho bạn", sub: "Kể lại nội dung video cho bạn cùng bàn nghe trong 1 phút, không nhìn bài viết.",
    body: `<div class="art-cue-card">Ghi âm lại nếu học online — nộp file cho giáo viên trước 21h.</div>` },
];

const body = `
<header class="art-ticket-header">
  <div>
    <p class="art-boarding">Video Learning Route · Unit 2</p>
    <div class="art-line-name">Airport Announcements — Listening Route</div>
    <div class="art-counter-row">
      <div class="art-counter"><span class="art-lbl">Thời lượng video</span><span class="art-val">3:20</span></div>
      <div class="art-counter"><span class="art-lbl">Số trạm</span><span class="art-val">6</span></div>
      <div class="art-counter"><span class="art-lbl">Thời gian ước tính</span><span class="art-val">25 phút</span></div>
    </div>
  </div>
</header>

<main class="art-shell">
  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">Overview</span>
      <h2>Bản đồ tuyến học</h2>
    </div>
    <div class="art-miniroute">
      ${stations
        .map(
          (s, i) => `
        <div class="art-station-marker"><span class="art-station-dot" style="--st-color:var(--art-${s.cat})"></span><span class="art-station-code">${s.code}</span></div>
        ${i < stations.length - 1 ? '<span class="art-track"></span>' : ""}
      `
        )
        .join("")}
    </div>
  </section>

  <section class="art-section">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">Video</span>
      <h2>Nguồn video</h2>
    </div>
    <div class="art-video-embed">
      <div class="art-play-badge"></div>
      <div class="art-video-note">Video placeholder — liên kết thật nằm trong metadata dành riêng cho giáo viên, không nhúng trực tiếp vào artifact tĩnh này.</div>
    </div>
  </section>

  <section class="art-section" style="margin-bottom:0;">
    <div class="art-section-head">
      <span class="art-section-eyebrow art-mono">Lộ trình</span>
      <h2>6 trạm học theo tuyến</h2>
    </div>
    ${stations
      .map(
        (s) => `
    <div class="art-station">
      <div class="art-station-rail"><span class="art-dot" style="--st-color:var(--art-${s.cat})"></span><span class="art-thread"></span></div>
      <div class="art-station-body art-${s.cat}" style="--st-color:var(--art-${s.cat})">
        <div class="art-station-head"><span class="art-station-code">${s.code}</span><span class="art-station-title">${s.title}</span></div>
        <p class="art-station-sub">${s.sub}</p>
        ${s.body}
      </div>
    </div>`
      )
      .join("\n")}
    <div class="art-counter-badge art-count-ok" style="margin-top:8px;">Tự đánh giá: 5/6 trạm hoàn thành tốt</div>
  </section>
</main>
${footer("Video Learning Route showcase · Issue 003")}
`;

writeFile("families/video-route.html", renderPage({ family: "transit-route", title: "Video Route — Airport Announcements", body }));
console.log("video-route family generated.");
