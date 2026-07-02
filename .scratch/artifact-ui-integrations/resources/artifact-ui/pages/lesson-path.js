const { renderPage, writeFile } = require("../render.js");
const { footer } = require("../partials.js");

const body = `
<div class="art-shell--split">
  <aside class="art-shell-aside">
    <div class="art-nav-brand"><span class="art-nav-dot">O</span> oh-my-class</div>
    <div class="art-nav-title">Lộ trình 8 tuần — Destination B2</div>
    <div class="art-nav-sub">Path Dossier · Lớp 11A3</div>
    <div class="art-stat-card" style="margin-bottom:16px;">
      <div class="art-k">Tiến độ hiện tại</div>
      <div class="art-v">Giai đoạn 2 <small>/ 4 giai đoạn</small></div>
    </div>
    <nav class="art-nav-list">
      <a href="#g1"><span class="art-nn">01</span> Giai đoạn 1 — Nền tảng</a>
      <a href="#g2" class="is-active"><span class="art-nn">02</span> Giai đoạn 2 — Mở rộng</a>
      <a href="#g3"><span class="art-nn">03</span> Giai đoạn 3 — Luyện đề</a>
      <a href="#g4"><span class="art-nn">04</span> Giai đoạn 4 — Nước rút</a>
    </nav>
    <div class="art-callout art-callout--dashed" style="margin-top:20px;">
      <span class="art-glyph art-mono">i</span>
      <span>Roadmap cập nhật theo kết quả kiểm tra định kỳ mỗi 2 tuần.</span>
    </div>
  </aside>

  <div class="art-shell-main">
    <header class="art-page-head">
      <p class="art-cover-eyebrow art-mono">Lesson / Path Dossier</p>
      <h1>Lộ trình luyện thi Destination B2 — Học kỳ 1</h1>
      <p class="art-lede">8 tuần, 4 giai đoạn, mỗi giai đoạn có mục tiêu đầu ra rõ ràng và một bài kiểm tra chốt trước khi sang giai đoạn kế tiếp.</p>
    </header>

    <section class="art-section">
      <div class="art-section-head">
        <span class="art-section-eyebrow art-mono">Mục tiêu</span>
        <h2>Mục tiêu học kỳ</h2>
      </div>
      <div class="art-objective-card">
        <div class="art-ot">Học sinh sẽ có thể</div>
        <ol>
          <li>Phân biệt chính xác 12 cụm từ vựng dễ nhầm theo chủ đề Travel &amp; Transport.</li>
          <li>Đạt tối thiểu 7.5/10 ở bài kiểm tra định dạng đề thi thật.</li>
          <li>Tự tin roleplay 3 tình huống hội thoại sân bay/nhà ga không cần script.</li>
        </ol>
      </div>
    </section>

    <section class="art-section">
      <div class="art-section-head">
        <span class="art-section-eyebrow art-mono">Roadmap</span>
        <h2>Timeline 4 giai đoạn</h2>
      </div>
      <div class="art-phase-rail">
        <div class="art-phase-block" style="--phase-color:var(--art-cat-1)">
          <span class="art-phase-dot" style="--phase-color:var(--art-cat-1)"></span>
          <div class="art-phase-card">
            <div class="art-phase-top"><span class="art-phase-when" style="--phase-color:var(--art-cat-1)">Tuần 1–2</span><h3 style="font-size:15.5px;margin:0;">Giai đoạn 1 — Nền tảng</h3></div>
            <div class="art-phase-goal">Xây nền 5 cụm từ vựng cốt lõi + ngữ pháp thì hiện tại hoàn thành.</div>
            <div class="art-phase-output">Đầu ra: bài kiểm tra 15 câu, ngưỡng đạt 7/10.</div>
          </div>
        </div>
        <div class="art-phase-block" style="--phase-color:var(--art-cat-2)">
          <span class="art-phase-dot" style="--phase-color:var(--art-cat-2)"></span>
          <div class="art-phase-card">
            <div class="art-phase-top"><span class="art-phase-when" style="--phase-color:var(--art-cat-2)">Tuần 3–4 · Đang diễn ra</span><h3 style="font-size:15.5px;margin:0;">Giai đoạn 2 — Mở rộng</h3></div>
            <div class="art-phase-goal">Thêm 7 cụm từ vựng nâng cao + roleplay hội thoại thực tế.</div>
            <div class="art-phase-output">Đầu ra: 3 buổi roleplay có ghi âm, tự chấm theo rubric.</div>
          </div>
        </div>
        <div class="art-phase-block" style="--phase-color:var(--art-cat-4)">
          <span class="art-phase-dot" style="--phase-color:var(--art-cat-4)"></span>
          <div class="art-phase-card">
            <div class="art-phase-top"><span class="art-phase-when" style="--phase-color:var(--art-cat-4)">Tuần 5–6</span><h3 style="font-size:15.5px;margin:0;">Giai đoạn 3 — Luyện đề</h3></div>
            <div class="art-phase-goal">Làm 4 đề thi thử theo đúng format và thời gian thi thật.</div>
            <div class="art-phase-output">Đầu ra: bảng phân tích lỗi sai theo từng nhóm câu hỏi.</div>
          </div>
        </div>
        <div class="art-phase-block" style="--phase-color:var(--art-cat-5)">
          <span class="art-phase-dot" style="--phase-color:var(--art-cat-5)"></span>
          <div class="art-phase-card">
            <div class="art-phase-top"><span class="art-phase-when" style="--phase-color:var(--art-cat-5)">Tuần 7–8</span><h3 style="font-size:15.5px;margin:0;">Giai đoạn 4 — Nước rút</h3></div>
            <div class="art-phase-goal">Ôn tập trọng điểm dựa trên lỗi sai thường gặp nhất của cả lớp.</div>
            <div class="art-phase-output">Đầu ra: bài kiểm tra tổng kết, mục tiêu ≥ 7.5/10.</div>
          </div>
        </div>
      </div>
    </section>

    <section class="art-section">
      <div class="art-section-head">
        <span class="art-section-eyebrow art-mono">Nội dung mẫu</span>
        <h2>Concept box — Giai đoạn 2</h2>
      </div>
      <div class="art-concept-box">
        <div class="art-cb-title">Present Perfect vs. Past Simple</div>
        <span class="art-cb-link">Liên hệ cụm travel/journey/trip đã học ở Giai đoạn 1</span>
        <div class="art-triad">
          <div class="art-triad-card"><b>Hình thức</b><span>have/has + V3</span></div>
          <div class="art-triad-card"><b>Trọng tâm</b><span>Kết quả hiện tại</span></div>
          <div class="art-triad-card"><b>Dấu hiệu</b><span>already, just, since, for</span></div>
        </div>
      </div>
    </section>

    <section class="art-section">
      <div class="art-section-head">
        <span class="art-section-eyebrow art-mono">Thực hành</span>
        <h2>Script roleplay — Tại quầy check-in</h2>
      </div>
      <div class="art-script">
        <div class="art-line"><span class="art-who art-who--a">Nhân viên</span><span class="art-what">Good morning! Can I see your <span class="art-blank">passport</span> and <span class="art-blank">ticket</span>, please?</span></div>
        <div class="art-line"><span class="art-who art-who--b">Hành khách</span><span class="art-what">Sure, here you are. I'd also like to know the boarding gate for this flight.</span></div>
        <div class="art-line"><span class="art-who art-who--a">Nhân viên</span><span class="art-what">You'll be boarding at gate 14. The <span class="art-blank">fare</span> difference for an aisle seat is ten dollars — would you like to upgrade?</span></div>
        <div class="art-script-key"><b>Đáp án chỗ trống:</b> passport, ticket, fare — ôn lại đúng 3 từ đã học ở Nhóm 02.</div>
      </div>
    </section>

    <section class="art-section" style="margin-bottom:0;">
      <div class="art-section-head">
        <span class="art-section-eyebrow art-mono">Bài tập về nhà</span>
        <h2>Homework — Tuần 3</h2>
      </div>
      <ul class="art-hw-list">
        <li><span class="art-hwtag">Viết</span> Viết đoạn văn 100 từ kể về một chuyến đi đáng nhớ, dùng đúng 3 trong 5 từ nhóm "chuyến đi".</li>
        <li><span class="art-hwtag">Nói</span> Ghi âm 1 phút roleplay tại quầy check-in với bạn cùng bàn.</li>
        <li><span class="art-hwtag">Ôn tập</span> Làm lại practice set Nhóm 01 &amp; 02 cho đến khi đạt 9/10.</li>
      </ul>
    </section>
  </div>
</div>
${footer("Lesson / Path Dossier showcase · Issue 003")}
`;

writeFile("families/lesson-path.html", renderPage({ family: "paper-dossier", title: "Path Dossier — Lộ trình Destination B2", body }));
console.log("lesson-path family generated.");
