// Transcript-derived content — Zamery, rooted-in-strength-learning,
// Future Perfect vs. Future Perfect Continuous, one running scenario
// ("9h tối mai, con mèo chạy qua"). Shared between:
//   - pages/core-primitives.js (Issue 004 AC: anchor-timeline and
//     controlled-comparison demoed with real transcript content, not
//     lorem ipsum)
//   - pages/root-cause-session.js (Issue 005: the full artifact)
// Single source of truth so both pages stay in sync, same reasoning as
// pages/semantic-vocabulary-data.js already applies to Issue 002.
//
// REAL vs. ILLUSTRATIVE: the scenario, both anchor timelines, the 4-way
// comparison, and both mastery markers are drawn from the actual
// transcript per issue-005's scope. The transcript is cut off before
// Zamery pushes back, proposes his own generalization, hits an
// exception, or needs a second metaphor — so the checkpoint, exception
// reveal, stress-test, and metaphor-log below are representative but
// invented, to demo primitives the transcript itself never reached.
// They are labeled "illustrative, not from the actual session" wherever
// they're rendered (see pages/root-cause-session.js) per issue-005's
// explicit instruction not to let invented content read as if it happened.

const scenario =
  "9 giờ tối mai, đúng lúc bạn đang ngồi học bài, một con mèo hàng xóm sẽ chạy vụt qua sân nhà bạn — như nó vẫn hay làm mỗi tối. Đứng tại đúng mốc 9h tối mai đó và quay đầu nhìn lại: bạn đã làm gì, đang làm gì, và làm được bao lâu rồi?";

const futurePerfectTimeline = {
  axisLabel: "Future Perfect — kéo mốc 9h tối mai, nhìn ngược lại",
  anchor: { label: "9:00 tối mai — mèo chạy qua sân" },
  events: [
    { label: "7:00 tối mai — bắt đầu ngồi học Toán", position: "before" },
    { label: "8:45 tối mai — làm xong, gấp sách lại", position: "before", state: "đã xong" },
  ],
};

const futurePerfectContinuousTimeline = {
  axisLabel: "Future Perfect Continuous — cùng một mốc, nhìn quá trình đang kéo dài",
  anchor: { label: "9:00 tối mai — mèo chạy qua sân" },
  events: [
    { label: "7:00 tối mai — bắt đầu ngồi học Toán", position: "before" },
    { label: "9:00 tối mai — vẫn đang học", position: "at", state: "chưa dừng" },
    { label: "9:05 tối mai — mèo đã khuất, vẫn học tiếp", position: "after" },
  ],
};

// The transcript's own closing "tóm lại mặt cắt tư duy của cả 4 thì" —
// one constant scenario, one axis (which aspect of "tương lai" is being
// marked), 4 real variants. This is the n=4 case Issue 005 needs.
const fourTenseComparison = {
  constant: { label: "Hằng số giữ nguyên", value: "9h tối mai · mèo chạy qua sân" },
  axis: "Biến duy nhất đổi: khía cạnh của thì tương lai được đánh dấu",
  variants: [
    {
      label: "Future Simple",
      value: "will play",
      note: "Chỉ là một sự thật sẽ xảy ra — không neo vào mốc 9h, không nhìn ngược.",
    },
    {
      label: "Future Continuous",
      value: "will be playing",
      note: "Đang diễn ra đúng tại 9h tối mai — đứng tại mốc, nhìn ngang, chưa nhìn ngược.",
    },
    {
      label: "Future Perfect",
      value: "will have played",
      note: "Đứng tại 9h tối mai, nhìn ngược: hành động ĐÃ XONG trước khi tới mốc.",
    },
    {
      label: "Future Perfect Continuous",
      value: "will have been playing for 2 hours",
      note: "Đứng tại 9h tối mai, nhìn ngược: quá trình đã kéo dài LIÊN TỤC 2 tiếng tính đến mốc.",
    },
  ],
};

// Extra comparison sets used only by the core-primitives showcase demo
// (Issue 004 AC: verified at n=2, n=3, n=4, n=6 — not just the n=4 case
// the transcript happens to need). n=2/n=3 slice the same real variants;
// n=6 extends the same real axis with two more real tenses for breadth.
const twoTenseComparison = {
  constant: fourTenseComparison.constant,
  axis: fourTenseComparison.axis,
  variants: fourTenseComparison.variants.slice(2, 4), // Future Perfect vs. FPC — the actual contrast this lesson teaches
};
const threeTenseComparison = {
  constant: fourTenseComparison.constant,
  axis: fourTenseComparison.axis,
  variants: fourTenseComparison.variants.slice(1, 4),
};
const sixTenseComparison = {
  constant: { label: "Hằng số giữ nguyên", value: "chủ thể + động từ \"play\"" },
  axis: "Biến duy nhất đổi: thì & khía cạnh (mở rộng quá khứ/hiện tại để so n=6)",
  variants: [
    { label: "Past Simple", value: "played", note: "Xảy ra và kết thúc trong quá khứ, không neo vào 9h tối mai." },
    { label: "Present Perfect", value: "has played", note: "Đã xảy ra, còn ảnh hưởng đến hiện tại — không phải mốc tương lai." },
    ...fourTenseComparison.variants,
  ],
};

// Mastery markers — the transcript ends with an open invitation to try a
// second scenario, not a closing signal (Rule #14), so both render
// "open", never "clicked" — no fabricated completion state.
const masteryMarkers = [
  { concept: "Future Perfect — will have + V3", state: "open" },
  { concept: "Future Perfect Continuous — will have been + V-ing", state: "open" },
];

const closingPrompt =
  "Thử áp dụng đúng khung tư duy \"giữ nguyên 1 mốc, chỉ đổi khía cạnh thì\" cho một tình huống mới: 6 giờ chiều mai, đúng lúc mẹ về đến nhà...";

// ---------- Illustrative-only content (explicitly not from the transcript) ----------

const illustrativeExceptionReveal = {
  prompt: "Xem trường hợp ngoại lệ",
  text:
    "Ngoại lệ: nếu hành động ở vế \"before\" là một trạng thái tĩnh (know, love, own...) thay vì một hành động có thể đếm/lặp, Future Perfect Continuous thường không tự nhiên — vẫn dùng Future Perfect thường (will have known), vì bản thân trạng thái tĩnh không có \"quá trình kéo dài\" để nhấn mạnh.",
};

const illustrativeCheckpoint = {
  learnerClaim: "Vậy là cứ có 'have/has been' + V-ing là Future Perfect Continuous, đúng không thầy?",
  verdict: "corrected",
  correction: "Gần đúng, nhưng thiếu chữ 'will' ở đầu — will have been + V-ing, vì đây vẫn là một mốc TƯƠNG LAI, chưa xảy ra.",
  explanation:
    "have/has been + V-ing (không có will) là Present Perfect Continuous — một thì khác hẳn, dùng cho việc đã và đang xảy ra tính đến HIỆN TẠI, không phải một mốc trong tương lai như 9h tối mai.",
};

const illustrativeStressTest = {
  learnerAttempt: "9h tối mai, con mèo will have chạy qua sân — thêm will have vào là chắc chắn đúng Future Perfect rồi đúng không?",
  breaksBecause:
    "will have phải đi với V3/-ed (will have run), không phải động từ chưa chia — câu này chỉ thêm đúng 2 từ \"will have\" mà bỏ qua việc động từ theo sau luôn phải ở dạng phân từ hoàn thành.",
  tiesBackTo: "Công thức gốc: S + will have + V3/-ed.",
};

const illustrativeMetaphorLog = {
  attempts: [
    {
      device: "Đường đua tiếp sức",
      text: "Ví thì như đường chạy tiếp sức — không rõ ai đang cầm gậy lúc nào, học sinh không hình dung được vị trí trên trục thời gian.",
      landed: false,
    },
    {
      device: "Đứng ở mốc, quay đầu nhìn lại",
      text: "Bạn đứng đúng tại 9h tối mai, quay đầu nhìn lại phía sau: thấy việc đã xong hẳn (Future Perfect) hay vẫn đang diễn ra kéo dài tới lúc đó (Future Perfect Continuous).",
      landed: true,
    },
  ],
};

module.exports = {
  scenario,
  futurePerfectTimeline,
  futurePerfectContinuousTimeline,
  fourTenseComparison,
  twoTenseComparison,
  threeTenseComparison,
  sixTenseComparison,
  masteryMarkers,
  closingPrompt,
  illustrativeExceptionReveal,
  illustrativeCheckpoint,
  illustrativeStressTest,
  illustrativeMetaphorLog,
};
