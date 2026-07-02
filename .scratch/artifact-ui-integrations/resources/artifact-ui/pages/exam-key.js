const { renderPage, writeFile, INTERACTIVITY_JS } = require("../render.js");
const { footer } = require("../partials.js");

const questions = [
  {
    n: 1,
    cat: "cat1",
    text: "The plane ___ before we arrived at the airport, so we missed our flight.",
    options: ["A. left", "B. had left", "C. has left", "D. was leaving"],
    correct: 1,
    essence:
      "Hành động 'left' xảy ra TRƯỚC một mốc quá khứ khác ('we arrived') → quá khứ hoàn thành.",
    trap: "A đúng thì nhưng sai trật tự thời gian — không thể hiện việc máy bay rời đi trước khi họ đến.",
    wrong: [
      { l: "A", opt: "left", why: "Quá khứ đơn — không thể hiện rõ hành động nào xảy ra trước." },
      {
        l: "C",
        opt: "has left",
        why: "Hiện tại hoàn thành không hợp với mốc thời gian quá khứ 'arrived'.",
      },
      {
        l: "D",
        opt: "was leaving",
        why: "Diễn tả hành động đang xảy ra, không phải đã hoàn tất trước đó.",
      },
    ],
  },
  {
    n: 2,
    cat: "cat2",
    text: 'A: "Could you tell me how much the ___ to the airport is?" B: "About 200,000 dong by taxi."',
    options: ["A. fare", "B. ticket", "C. fee", "D. cost"],
    correct: 0,
    essence:
      "Hỏi giá cho một chuyến di chuyển bằng phương tiện (taxi) → Fare, không phải Fee (dịch vụ/tổ chức).",
    trap: "C 'fee' hay bị chọn nhầm vì cũng là 'tiền phải trả', nhưng fee không gắn với phương tiện di chuyển.",
    wrong: [
      {
        l: "B",
        opt: "ticket",
        why: "Ticket là vật thể, không dùng để hỏi 'how much' trực tiếp theo cách này.",
      },
      { l: "C", opt: "fee", why: "Fee dùng cho dịch vụ/tổ chức, không phải tiền taxi." },
      {
        l: "D",
        opt: "cost",
        why: "Cost là từ chung chung hơn — câu này cần từ chuyên biệt trong cụm đã học.",
      },
    ],
  },
  {
    n: 3,
    cat: "cat3",
    text: 'Rewrite: "They didn\'t compensate her for the damaged luggage." → "She ___"',
    options: [
      "A. wasn't compensated for the damaged luggage.",
      "B. didn't compensate for the damaged luggage.",
      "C. hasn't been compensating the damaged luggage.",
      "D. isn't compensated the damaged luggage.",
    ],
    correct: 0,
    essence: "Chuyển câu chủ động → bị động, giữ nguyên thì quá khứ đơn: was/were + not + V3.",
    trap: "B giữ nguyên dạng chủ động dù đã đổi chủ ngữ — lỗi phổ biến khi học sinh chỉ đổi chủ ngữ mà quên đổi động từ.",
    wrong: [
      {
        l: "B",
        opt: "didn't compensate for...",
        why: "Vẫn ở dạng chủ động — thiếu 'was/were + V3'.",
      },
      {
        l: "C",
        opt: "hasn't been compensating...",
        why: "Sai thì — đề bài ở quá khứ đơn, không phải hiện tại hoàn thành tiếp diễn.",
      },
      { l: "D", opt: "isn't compensated...", why: "Sai thì — dùng hiện tại thay vì quá khứ." },
    ],
  },
  {
    n: 4,
    cat: "cat4",
    text: 'Fill in: "After a long ___ across the desert, the caravan finally reached the oasis, exhausted but relieved."',
    options: ["A. voyage", "B. journey", "C. trip", "D. travel"],
    correct: 1,
    essence:
      "Nhấn mạnh quá trình di chuyển dài, gian khổ, qua nhiều chặng ('across the desert') → Journey.",
    trap: "A 'voyage' hay bị chọn vì cũng chỉ chuyến đi dài, nhưng voyage luôn gắn với tàu thủy/phi thuyền, không phải đi bộ/lạc đà qua sa mạc.",
    wrong: [
      {
        l: "A",
        opt: "voyage",
        why: "Chỉ dùng cho phương tiện lớn (tàu/phi thuyền), không hợp với 'caravan across the desert'.",
      },
      {
        l: "C",
        opt: "trip",
        why: "Trip ngắn ngày, có mục đích rõ ràng — không hợp với 'long ... exhausted'.",
      },
      { l: "D", opt: "travel", why: "Travel không đếm được — không thể dùng sau 'a long ___'." },
    ],
  },
];

const groupLegend = [
  { cat: "cat1", label: "Ngữ pháp — thì động từ", range: "Câu 1" },
  { cat: "cat2", label: "Hội thoại — tiền vé", range: "Câu 2" },
  { cat: "cat3", label: "Viết lại câu", range: "Câu 3" },
  { cat: "cat4", label: "Điền từ — chuyến đi", range: "Câu 4" },
];

// Issue 006: the answer/explanation panel is gated behind its own
// per-question reveal button (`.art-reveal-btn`, generic contract 1 in
// interactivity.js) and opted into the "exam-answers" group so the
// sidebar's `.art-mode-toggle` (contract 2) can bulk reveal/hide every
// panel at once. `.art-option--correct` stays statically visible —
// this is the Teacher Edition, so which option is correct is never
// gated; only the essence/trap/wrong-answer explanation is.
function qcard(q) {
  const opts = q.options
    .map(
      (o, i) =>
        `<div class="art-option${i === q.correct ? " art-option--correct" : ""}"><span class="art-letter">${o[0]}</span><span>${o.slice(3)}</span></div>`,
    )
    .join("\n");
  const panelId = `panel-q${q.n}`;
  return `
  <div class="art-qcard art-jump-target art-g-${q.cat} art-avoid-break" id="q${q.n}" tabindex="-1">
    <div class="art-qhead"><span class="art-qnum">Câu ${q.n}</span><span class="art-qtext">${q.text}</span></div>
    <div class="art-options">${opts}</div>
    <button type="button" class="art-reveal-btn art-no-print" data-toggle-reveal data-toggle-group="exam-answers"
      aria-controls="${panelId}" aria-expanded="false"
      data-collapsed-label="Xem đáp án &amp; giải thích" data-expanded-label="Ẩn đáp án &amp; giải thích"
      style="margin-top:var(--art-space-3);">Xem đáp án &amp; giải thích</button>
    <div class="art-panel art-reveal-target" id="${panelId}" hidden>
      <div class="art-prow art-prow--essence"><span class="art-plabel">Bản chất</span><span class="art-ptext">${q.essence}</span></div>
      <div class="art-prow"><span class="art-plabel">Bẫy hay gặp</span><span class="art-ptext">${q.trap}</span></div>
      <div class="art-wrong-section">
        <span class="art-wrong-section-label">Vì sao các phương án khác sai</span>
        ${q.wrong.map((w) => `<div class="art-wrong-item"><span class="art-wletter">${w.l}.</span><span class="art-wreason"><span class="art-woption">${w.opt}</span> — ${w.why}</span></div>`).join("\n")}
      </div>
    </div>
  </div>`;
}

const body = `
<div class="art-shell--split">
  <aside class="art-shell-aside">
    <div class="art-nav-brand"><span class="art-nav-dot">O</span> oh-my-class</div>
    <div class="art-nav-title">Đề kiểm tra 15 phút — Unit 2</div>
    <div class="art-nav-sub">Answer Key · Teacher Edition</div>
    <div class="art-jumpbox art-no-print" style="margin-bottom:6px;">
      <input type="text" inputmode="numeric" placeholder="Câu #" id="jumpToQuestion"
        data-jump-input-el data-jump-status="jumpStatus" aria-label="Nhảy tới số câu" />
      <button type="button" class="art-reveal-btn art-no-print" data-jump-go data-jump-input="jumpToQuestion"
        style="padding:6px 12px;">→</button>
    </div>
    <p id="jumpStatus" aria-live="polite" class="art-no-print" style="font-size:11px;color:var(--art-ink-faint);font-family:var(--art-font-mono);min-height:14px;margin:0 0 16px;"></p>
    <button type="button" class="art-mode-toggle art-no-print" role="switch" aria-checked="false"
      data-mode-toggle data-toggles-group="exam-answers" style="margin-bottom:18px;">
      <span class="art-switch"></span> Hiện đáp án
    </button>
    <div class="art-side-legend" style="display:flex;flex-direction:column;gap:6px;">
      ${groupLegend
        .map(
          (
            g,
          ) => `<div style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--art-ink-soft);">
            <span style="width:9px;height:9px;border-radius:50%;background:var(--art-${g.cat});flex-shrink:0;"></span>
            <span>${g.label} <span style="color:var(--art-ink-faint)">(${g.range})</span></span>
          </div>`,
        )
        .join("\n")}
    </div>
  </aside>

  <div class="art-shell-main">
    <header class="art-page-head">
      <p class="art-cover-eyebrow art-mono">Exam Answer Key</p>
      <h1>Đề kiểm tra 15 phút — Unit 2: Travel &amp; Transport</h1>
      <p class="art-lede">4 câu mẫu, mỗi câu có đáp án, giải thích bản chất, bẫy hay gặp và lý do sai của từng phương án còn lại.</p>
    </header>

    <div class="art-qgrid art-no-print" style="margin-bottom:32px;max-width:260px;">
      ${questions.map((q) => `<button type="button" class="art-g-${q.cat}" data-jump-to="${q.n}" aria-label="Nhảy tới câu ${q.n}">${q.n}</button>`).join("")}
    </div>

    ${questions.map(qcard).join("\n")}
  </div>
</div>
${footer("Exam Answer Key showcase · Issue 003")}
`;

writeFile(
  "families/exam-key.html",
  renderPage({
    family: "paper-dossier",
    title: "Answer Key — Unit 2 Quiz",
    body,
    script: INTERACTIVITY_JS,
  }),
);
console.log("exam-key family generated.");
